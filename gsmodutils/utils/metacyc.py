import os
from collections import defaultdict, Counter
from gsmodutils.utils.io import load_model
from cobra import Reaction, Metabolite, Model
from cobra.io import save_json_model
import sys


def parse_db(db_path):
    """ Parse metacyc dat files to build dict containing entries """
    compounds_path = os.path.join(db_path, 'compounds.dat')
    enzymes_path = os.path.join(db_path, 'enzrxns.dat')
    reactions_path = os.path.join(db_path, 'reactions.dat')

    database = dict(
        compounds=parse_metacyc_file(compounds_path, ["UNIQUE-ID", "INCHI", "SMILES", "INCHI-KEY"]),
        reactions=parse_metacyc_file(reactions_path, ["UNIQUE-ID", "REACTION-DIRECTION"]),
        enzymes=parse_metacyc_file(enzymes_path, ["UNIQUE-ID"]),
    )
    return database


class FileEncodingCtx(object):

    def __init__(self, filename, encoding='latin-1', **kwargs):
        """
        Python 2 and 3 context manager for opening latin-1 encoded files
        Parsing Metacyc .dat files breaks opening files in python 3
        """
        self.filename = filename
        self.encoding = encoding
        self.kwargs = kwargs

    def __enter__(self):
        if sys.version_info[0] < 3:
            self.open_file = open(self.filename, **self.kwargs)
        else:
            self.open_file = open(self.filename, encoding=self.encoding, **self.kwargs)

        return self.open_file

    def __exit__(self, exec_type, exec_value, traceback):
        self.open_file.close()
        return self.open_file


def parse_metacyc_file(fpath, unique_fields):
    """
    Parses a dat file
    :str fpath: path to dat file
    :list unique_fields: list of fields that there should only be a single item of in each entry
    :return:
    """
    db = dict()

    with FileEncodingCtx(fpath) as datfile:
        entry = defaultdict(list)
        lprev = None
        for line in datfile:
            line = line.strip()
            # Comments
            if line[0] == "#":
                continue

            elif line[:2] == "//":
                # New entries, adjust old
                for it in unique_fields:
                    if it in entry:
                        entry[it] = entry[it][0]

                db[entry["UNIQUE-ID"]] = dict(entry)
                entry = defaultdict(list)
            else:
                spt = line.split(" - ")
                if len(spt) < 2:
                    continue

                it = spt[0]
                val = str(spt[1])
                entry[it].append(val)
                if it == "^COEFFICIENT" and lprev is not None:
                    # repeat the last entry in metabolites
                    try:
                        coef = int(val)
                    except ValueError:
                        coef = 1
                    entry[lprev[0]] += (coef - 1) * [lprev[1]]
                    lprev = None
                elif it in ["LEFT", "RIGHT"]:
                    lprev = (it, val)
                else:
                    lprev = None

    return db


def add_pathway(model, enzyme_ids=None, reaction_ids=None, db_path=None, copy=False):
    """
    For a given model add enzymes from metacyc database
    :param model: cobra model object
    :param enzyme_ids: list of EC entires in format ["EC-x.x.x.x", ...]
    :param reaction_ids: set of reaction ids to add to model
    :param db_path: path to the metacyc dat files on disk
    :param copy:
    :return:
    """
    if copy:
        model = model.copy()

    db = parse_db(db_path)

    if enzyme_ids is None:
        enzyme_ids = []

    if reaction_ids is None:
        reaction_ids = []

    # map enzyme ids to reactions
    for eid in enzyme_ids:
        erids = get_enzyme_reactions(eid, db)
        reaction_ids += erids

    added_reactions = []
    added_metabolites = []
    for rid in set(reaction_ids):
        if rid not in model.reactions:
            react, ametabolites = add_reaction(model, rid, db)
            added_reactions.append(react)
            added_metabolites += added_metabolites

    added_boundaries = []
    for react in added_reactions:
        for metabolite in react.metabolites:
            # Check if orphan. if so, add transporter out
            if len(metabolite.reactions) == 1:
                rb = model.add_boundary(metabolite, type='exchange')
                added_boundaries.append(rb)

    rdict = dict(
        model=model,
        added_reactions=added_reactions,
        added_metabolites=added_metabolites,
        added_boundaries=added_boundaries,
    )

    return rdict


def get_enzyme_reactions(eid, db):
    """
    For a given ec number return associated reaction ids
    :param eid: enzyme id format "EC-x.x.x.x"
    :param db: database dict
    :return:
    """
    erids = []

    if eid[:3] != "EC-":
        eid = "EC-{}".format(eid)

    for rid, react in db['reactions'].items():
        if 'EC-NUMBER' in react and eid in react['EC-NUMBER']:
            erids.append(rid)

    return erids


def add_reaction(model, reaction_id, db):
    """
    Add a metacyc reaction id to a cobrapy model
    :param model: cobrapy model instance
    :param reaction_id: reaction identifier in metacyc
    :param db: dictionary db object
    :return: tuple(reaction, added_metabolites) cobrapy Reaction and Metabolite instances
    """
    metabolites = dict()
    reaction = Reaction(reaction_id)

    dbr = db['reactions'][reaction_id]
    for mid, coef in Counter(dbr['LEFT']).items():
        mid = mid.replace('|', '')
        metabolites[mid] = coef

    for mid, coef in Counter(dbr['RIGHT']).items():
        mid = mid.replace('|', '')
        metabolites[mid] = -1 * coef

    model.add_reaction(reaction)
    added_metabolites = []
    for mid in metabolites:
        if mid not in model.metabolites:
            try:
                cpd = db['compounds'][mid]
            except KeyError:
                # Handles missing metabolites
                cpd = {"COMMON-NAME": mid}

            m = Metabolite(id=mid)
            m.name =cpd['COMMON-NAME']
            m.annotation = dict(metacyc_data=cpd)
            model.add_metabolites([m])
            added_metabolites.append(mid)

    reaction.add_metabolites(metabolites)
    if 'REACTION-DIRECTION' in dbr and dbr['REACTION-DIRECTION'] in ['LEFT-TO-RIGHT', 'PHYSIOL-LEFT-TO-RIGHT']:
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 0
    elif 'REACTION-DIRECTION' in dbr and dbr['REACTION-DIRECTION'] in ['RIGHT-TO-LEFT', 'PHYSIOL-RIGHT-TO-LEFT']:
        reaction.lower_bound = 0
        reaction.upper_bound = 1000.0
    else:
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 1000.0

    reaction.annotation = dict(metacyc_data=dbr)  # TODO: Add enzyme identifiers

    return reaction, added_metabolites


def build_universal_model(path, use_cache=True):
    """
    Constructs a universal model from all the reactions in the metacyc database

    :param path: path to folder containing metacyc dat files
    :param use_cache: optionally store the resulting model in cached form
    :return:
    """
    cache_location = '.metacyc_universal.json'

    try:
        if use_cache and os.path.exists(cache_location):
            model = load_model(cache_location)
            return model
    except (IOError, TypeError):
        pass  # This means cached model couldn't be loaded, we'll create a new one

    db = parse_db(path)
    model = Model()
    for reaction_id in db['reactions']:
        try:
            add_reaction(model, reaction_id, db)
        except KeyError:
            # Exception handling ignores badly formatted reactions
            pass

    if use_cache:
        save_json_model(model, cache_location)

    return model
