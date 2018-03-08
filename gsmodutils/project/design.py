import json
import os

import cobra
import pandas

from gsmodutils.exceptions import DesignError
import gsmodutils
import logging

logger = logging.getLogger(__name__)


class StrainDesign(object):
    def __init__(self, did, name, description, project, parent=None, reactions=None, metabolites=None, genes=None,
                 removed_metabolites=None, removed_reactions=None, removed_genes=None, base_model=None,
                 conditions=None):
        """
        Class for handling strain designs created by the project

        Mainly the useful functionality of this over dicts is validation, relationship to projects, creating the models
        as well as displaying the contents as a pandas dataframe

        :param project: Where project is None, the model will not be able to
        """
        self._as_model = None

        self.project = project
        self.base_model = base_model

        self.id = did
        self.name = name
        self.description = description

        self._reactions = reactions
        if self._reactions is None:
            self._reactions = []

        self._metabolites = metabolites
        if self._metabolites is None:
            self._metabolites = []

        self._genes = genes
        if self._genes is None:
            self._genes = []

        self._removed_metabolites = removed_metabolites
        if self._removed_metabolites is None:
            self._removed_metabolites = []

        self._removed_reactions = removed_reactions
        if self._removed_reactions is None:
            self._removed_reactions = []

        self._removed_genes = removed_genes
        if self._removed_genes is None:
            self._removed_genes = []

        self.conditions = conditions

        self.parent = parent
        self.check_parents()

        self._p_model = None

    def check_parents(self, p_stack=None):
        """ Tests to see if their is a loop in parental inheritance"""
        if p_stack is None:
            p_stack = []

        if self.id in p_stack:
            raise DesignError('Error in design {id} - has a cyclical reference')

        p_stack.append(self.id)

        if self.parent is None:
            return True

        if not isinstance(self.parent, StrainDesign):
            raise TypeError('invalid parent design')

        return self.parent.check_parents(p_stack)

    @property
    def reactions(self):
        """Recursively builds set of reactions inherited from parents"""
        if self.parent is None:
            return self._reactions
        return self.parent.reactions + self._reactions

    @property
    def metabolites(self):
        """Recursively builds set of metabolites inherited from parents"""
        if self.parent is None:
            return self._metabolites
        return self.parent.metabolites + self._metabolites

    @property
    def genes(self):
        """Recursively builds set of genes inherited from parents"""
        if self.parent is None:
            return self._genes
        return self.parent.genes + self._genes

    @property
    def removed_reactions(self):
        """Recursively builds set of removed reactions inherited from parents"""
        if self.parent is None:
            return self._removed_reactions
        return self.parent.removed_reactions + self._removed_reactions

    @property
    def removed_metabolites(self):
        """Recursively builds set of removed metabolites inherited from parents"""
        if self.parent is None:
            return self._removed_metabolites
        return self.parent.removed_metabolites + self._removed_metabolites

    @property
    def removed_genes(self):
        """Recursively builds set of removed genes inherited from parents"""
        if self.parent is None:
            return self._removed_genes
        return self.parent.removed_genes + self._removed_genes

    def reactions_dataframe(self):
        """
        Return a dataframe of the reactions involved in the design
        :return:
        """
        p_model = self.as_pathway_model()
        df = dict(lower_bound=[], upper_bound=[], reaction_string=[], id=[])
        index = []
        for i, reaction in enumerate(p_model.reactions):
            df["id"].append(reaction.id)
            df["upper_bound"].append(reaction.upper_bound)
            df["lower_bound"].append(reaction.lower_bound)
            df["reaction_string"].append(str(reaction))
            index.append(i)

        df = pandas.DataFrame(df, index=index)
        return df

    def metabolites_dataframe(self):
        """
        Return a dataframe of the reactions involved in the design
        :return:
        """
        p_model = self.as_pathway_model()
        df = dict(reactions=[], id=[], name=[])
        index = []
        for i, metabolite in enumerate(p_model.metabolites):
            df["id"].append(metabolite.id)
            df["name"].append(metabolite.name)
            df["reactions"].append(metabolite.reactions)
            index.append(i)

        df = pandas.DataFrame(df, index=index)
        return df

    def genes_dataframe(self):
        """
        Return a dataframe of the reactions involved in the design
        :return:
        """
        p_model = self.as_pathway_model()
        df = dict(reactions=[], id=[], name=[])
        index = []
        for i, gene in enumerate(p_model.genes):
            df["id"].append(gene.id)
            df["name"].append(gene.name)
            df["reactions"].append(gene.reactions)
            index.append(i)

        df = pandas.DataFrame(df, index=index)
        return df

    def to_dict(self):
        """
        Converts to design dict (compatible with model diffs)
        :return:
        """
        p_id = None
        if self.parent is not None:
            p_id = self.parent.id

        rdict = dict(
            id=self.id,
            parent=p_id,
            reactions=self.reactions,
            removed_reactions=self.removed_reactions,
            metabolites=self.metabolites,
            removed_metabolites=self.removed_metabolites,
            genes=self.genes,
            name=self.name,
            description=self.description,
            base_model=self.base_model,
            conditions=self.conditions,
        )
        return rdict

    @classmethod
    def from_json(cls, did, file_path, project):
        """
        Load from a json file
        :param did unique design identifier
        :param file_path: file location of design
        :param project: GSMProject project instance
        :return:
        """
        with open(file_path) as fp:
            design = json.load(fp)
        # Makes sure fields are validated
        return cls.from_dict(did, design, project)

    @classmethod
    def from_dict(cls, did, design, project):
        """
        :param did: unique design identifier
        :param design: design dict
        :param project: GSMProject instance
        :return:
        """
        cls.validate_dict(design)

        parent = design['parent']
        if parent is not None:
            parent = project.get_design(parent)

        this = cls(
            did=did,
            name=design['name'],
            description=design['description'],
            project=project,
            parent=parent,
            reactions=design['reactions'],
            metabolites=design['metabolites'],
            removed_metabolites=design['removed_metabolites'],
            removed_reactions=design['removed_reactions'],
            genes=design['genes'],
            base_model=design['base_model'],
            conditions=design['conditions'],
        )

        return this

    def to_json(self, file_path, overwrite=False):
        """ Write to a given file """
        if not overwrite and os.path.exists(file_path):
            raise IOError("Existing file exists in design path and overwrite flag is False")

        with open(file_path, "w+") as jsn_f:
            json.dump(self.to_dict(), jsn_f, indent=4)

    def load(self):
        """
        Returns a cobra model containing the parent model with the design applied
        :return:
        """
        if self.project is None:
            raise DesignError("No specified project or model.")

        model = self.project.load_model(self.base_model)

        # Add reactions/genes from design to existing model
        self.add_to_model(model)

        if self.conditions is not None:
            try:
                self.project.load_conditions(self.conditions, model=model)
            except KeyError:
                logger.warning('Cannot find conditions id {} in project specified by design'.format(self.conditions))

        return model

    def as_pathway_model(self):
        """
        Loads a cobra model with just the reactions present in this design
        Can be useful for the cobra.Model methods


        # TODO: add full metabolite info from parent model (optional, as it will be slower)
        :return: mdl instance of cobra.Model
        """

        if self._p_model is not None:
            return self._p_model

        mdl = cobra.Model()
        mdl.id = ''
        mdl = self.add_to_model(mdl, add_missing=True)
        self._p_model = mdl

        return self._p_model

    def add_to_model(self, model, copy=False, add_missing=True):
        """
        Add this design to a given cobra model
        :param model:
        :param copy:
        :param add_missing: add missing metabolites to the model
        :return:
        """

        if not isinstance(model, cobra.Model):
            raise TypeError('Expected cobra model')

        mdl = model
        if copy:
            mdl = model.copy()

        if isinstance(mdl, gsmodutils.GSModutilsModel):
            mdl.set_design(self)

        # Load parent design first
        if self.parent is not None:
            self.parent.add_to_model(model)

        # Add new or changed metabolites to model
        for metabolite in self.metabolites:
            # create new metabolite object if its not in the model already
            if metabolite['id'] in mdl.metabolites:
                metab = mdl.metabolites.get_by_id(metabolite['id'])
            else:
                metab = cobra.Metabolite()

            # Doesn't check any of these properties for differences, just update them
            metab.id = metabolite['id']
            metab.name = metabolite['name']
            metab.charge = metabolite['charge']
            metab.formula = metabolite['formula']
            metab.notes = metabolite['notes']
            metab.annotation = metabolite['annotation']
            metab.compartment = metabolite['compartment']

            if metab.id not in mdl.metabolites:
                mdl.add_metabolites([metab])

        # Add new or changed reactions to model
        for rct in self.reactions:
            if rct['id'] in mdl.reactions:
                reaction = mdl.reactions.get_by_id(rct['id'])
                reaction.remove_from_model()

            reaction = cobra.Reaction()
            reaction.id = rct['id']

            reaction.name = rct['name']
            reaction.lower_bound = rct['lower_bound']
            reaction.upper_bound = rct['upper_bound']

            reaction.gene_reaction_rule = rct['gene_reaction_rule']
            reaction.subsystem = rct['subsystem']
            reaction.name = rct['name']
            reaction.variable_kind = rct['variable_kind']

            mdl.add_reactions([reaction])
            reaction = mdl.reactions.get_by_id(reaction.id)

            metabolites = dict([(str(x), v) for x, v in rct['metabolites'].items()])

            if add_missing:
                for mid in metabolites:
                    try:
                        mdl.metabolites.get_by_id(mid)
                    except KeyError:
                        metab = cobra.Metabolite(id=mid)
                        mdl.add_metabolites(metab)

            reaction.add_metabolites(metabolites)
            reaction.objective_coefficient = rct['objective_coefficient']

        # delete removed metabolites/reactions
        for rtid in self.removed_reactions:
            try:
                reaction = mdl.reactions.get_by_id(rtid)
                reaction.remove_from_model()
            except KeyError:
                pass

        for metid in self.removed_metabolites:
            try:
                met = mdl.metabolites.get_by_id(metid)
                met.remove_from_model()
            except KeyError:
                pass
        mdl.id += "::{}".format(self.id)

        # Add gene annotation
        for gene in self.genes:

            try:
                gobj = model.genes.get_by_id(gene['id'])
            except KeyError:
                # genes should already be contained in the model if they have a reaction relationship
                # However, tolerate bad designs
                continue
            gobj.name = gene['name']
            gobj.functional = gene['functional']
            gobj.annotation = gene['annotation']
            gobj.notes = gene['notes']

        return mdl

    @staticmethod
    def validate_dict(design_dict, throw_exceptions=True):
        """
        Check required fields are present
        :param design_dict:
        :param throw_exceptions:
        :return:
        """
        required_fields = ["name", "description", "metabolites", "reactions", "genes"]
        for field in required_fields:
            if field not in design_dict:
                if not throw_exceptions:
                    return False
                raise DesignError("Required field {} missing from design".format(field))

        # TODO: test if reactions are valid
        # TODO: test if metabolites are valid
        # TODO: test genes are valid
        return True

    @property
    def info(self):
        pid = None
        if self.parent is not None:
            pid = self.parent.id
        info = dict(
            name=self.name,
            id=self.id,
            description=self.description,
            reactions=len(self.reactions),
            genes=len(self.genes),
            metabolites=len(self.metabolites),
            parent=pid,
        )
        return info

    def _repr_html_(self):
        """Method intended for jupyter notebooks"""
        info_str = "<table>"
        for k, v in self.info.items():
            info_str += "<tr> <td> <strong> {0} </strong> </td> <td> {1} </td> </tr>".format(k, v)
        info_str += "</table>"
        return info_str

    def __repr__(self):
        repr_s = "< StraignDesign {id} with {reactions} reactions, {genes} genes and {metabolites} metabolites>".format(
            **self.info
        )
        return repr_s
