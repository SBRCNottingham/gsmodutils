from cobra import Reaction, Metabolite
import os
from collections import defaultdict, Counter


def parse_db(db_path):
    compounds_path = os.path.join(db_path, 'compounds.dat')
    enzymes_path = os.path.join(db_path, 'enzrxns.dat')
    reactions_path = os.path.join(db_path, 'reactions.dat')

    database = dict(
        compounds=parse_metacyc_file(compounds_path, ["UNIQUE-ID", "INCHI", "SMILES", "INCHI-KEY"]),
        reactions=parse_metacyc_file(reactions_path, ["UNIQUE-ID", "REACTION-DIRECTION"]),
        enzymes=parse_metacyc_file(enzymes_path, ["UNIQUE-ID"]),
    )
    return database


def parse_metacyc_file(fpath, unique_fields):
    db = dict()

    with open(fpath) as datfile:
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
                val = spt[1]
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
    """For a given model add enzymes"""

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
    """For a given ec number return associated reaction ids"""
    erids = []

    for rid, react in db['reactions'].items():
        if 'EC-NUMBER' in react and eid in react['EC-NUMBER']:
            erids.append(rid)

    return erids


def add_reaction(model, reaction_id, db):

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
            m = Metabolite(id=mid)
            m.name = db['compounds'][mid]['COMMON-NAME']
            # TODO: add other metabolite info
            model.add_metabolites([m])
            added_metabolites.append(mid)

    reaction.add_metabolites(metabolites)
    if dbr['REACTION-DIRECTION'] in ['LEFT-TO-RIGHT', 'PHYSIOL-LEFT-TO-RIGHT']:
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 0
    elif dbr['REACTION-DIRECTION'] in ['RIGHT-TO-LEFT', 'PHYSIOL-RIGHT-TO-LEFT']:
        reaction.lower_bound = 0
        reaction.upper_bound = 1000.0
    else:
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 1000.0

    return reaction, added_metabolites
