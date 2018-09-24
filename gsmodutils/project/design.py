import json
import os

import cobra
import pandas

from gsmodutils.exceptions import DesignError, DesignOrphanError, DesignNotFoundError
from gsmodutils.model_diff import model_diff
import logging
from six import exec_
import jsonschema


logger = logging.getLogger(__name__)


class StrainDesign(object):

    design_schema = {
        "type": "object",
        "description": "JSON representation of gsmodutils designs. Largely based on COBRApy JSON schema",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "reactions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "metabolites": {
                            "type": "object",
                            "patternProperties": {
                                ".*": {"type": "number"},
                            }
                        },
                        "gene_reaction_rule": {"type": "string"},
                        "lower_bound": {"type": "number"},
                        "upper_bound": {"type": "number"},
                        "objective_coefficient": {
                            "type": "number",
                            "default": 0,
                        },
                        "variable_kind": {
                            "type": "string",
                            "pattern": "integer|continuous",
                            "default": "continuous"
                        },
                        "subsystem": {"type": "string"},
                        "notes": {"type": "object"},
                        "annotation": {"type": "object"},
                    },
                    "required": ["id", "name", "metabolites", "lower_bound",
                                 "upper_bound", "gene_reaction_rule"]
                }
            },
            "metabolites": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": ["string", "array"], "item": {"type": "string"} },
                        "compartment": {
                            "type": ["string", "null"],
                            "pattern": "[a-z]{1,2}"
                        },
                        "charge": {"type": ["integer", "null"]},
                        "formula": {"type": ["string", "null"]},
                        "_bound": {
                            "type": "number",
                            "default": 0
                        },
                        "_constraint_sense": {
                            "type": "string",
                            "default": "E",
                            "pattern": "E|L|G",
                        },
                        "notes": {"type": "object"},
                        "annotation": {"type": "object"},
                    },
                    "required": ["id", "name", "compartment"]
                }

            },
            "genes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "notes": {"type": "object"},
                        "annotation": {"type": "object"},
                    },
                    "required": ["id", "name"],
                }

            },

            "conditions": {"type": ["string", "null"]},
            "removed_metabolites": {
                "type": "array"
            },
            "removed_reactions": {
                "type": "array"
            },
            "removed_genes": {
                "type": "array"
            },

            "parent": {"type": ["string", "null"]},
        },
        "required": ["id", "name", "description", "reactions", "metabolites", "genes"]
    }

    def __init__(self, did, name, description, project, parent=None, reactions=None, metabolites=None, genes=None,
                 removed_metabolites=None, removed_reactions=None, removed_genes=None, base_model=None,
                 conditions=None, is_pydesign=False, design_func=None):
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

        self.is_pydesign = is_pydesign
        self.design_func = design_func

        if self.is_pydesign and not hasattr(self.design_func, '__call__'):
            raise DesignError("Python designs require a design function to be passed, got  type {}".format(
                type(design_func)))

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

    @staticmethod
    def compile_pydesign(pyfile):
        """
        Compile a python file and load any gsmodutil design names
        :param pyfile:
        :return:
        """
        logger.info("Loading python design file {}".format(pyfile))
        des_prefix = os.path.basename(pyfile).replace("design_", "").replace(".py", "")
        dnames = {}
        with open(pyfile) as codestr:
            try:
                compiled_code = compile(codestr.read(), '', 'exec')
            except SyntaxError as ex:
                # syntax error for user written code
                # ex.lineno, ex.msg, ex.filename, ex.text, ex.offset
                logger.error("Cannot load designs in pyfile {} due to synatx error\n{}".format(pyfile, ex))
                return dict(), None

        f_prefix = "gsmdesign_"
        df = lambda f: f[:len(f_prefix)] == f_prefix
        # filter for specific design functions
        for func in filter(df, compiled_code.co_names):
            dname = "{}_{}".format(des_prefix, func.replace(f_prefix, ""))
            dnames[dname] = func

        return dnames, compiled_code

    @staticmethod
    def _exec_pydesign(func_name, compiled_code):
        """
        :param func_name: function name
        :param compiled_code: python code compiled with `compile`
        :return: function
        """
        global_namespace = dict(
            __name__='__gsmodutils_design_loader__',
        )
        # Get the function from the file
        try:
            exec_(compiled_code, global_namespace)
        except Exception as ex:
            print(compiled_code)
            raise DesignError("Code execution error in file for {} {}".format(func_name, ex))

        if func_name not in global_namespace:
            raise DesignError("function {} not found in python file".format(func_name))

        func = global_namespace[func_name]

        if not hasattr(func, '__call__'):
            raise DesignError("Design function must be callable, got type {}".format(type(func)))

        return func

    @classmethod
    def from_pydesign(cls, project, did, func_name, compiled_code):
        """ Load a pydesign function as a proper design """
        func = cls._exec_pydesign(func_name, compiled_code)

        # Set default variables
        func.name = getattr(func, 'name', "")
        func.parent = getattr(func, 'parent', None)
        func.description = getattr(func, 'description', func.__doc__)
        func.base_model = getattr(func, 'base_model', None)
        func.conditions = getattr(func, 'conditions', None)

        # Will throw error if parent is not a valid design
        parent = None
        if func.parent is not None:
            try:
                parent = project.get_design(func.parent)
            except DesignError:
                raise DesignOrphanError("Design parent appears to be invalid {} --> {}".format(func.parent, did))
            except DesignNotFoundError:
                raise DesignOrphanError("Design parent not found {} --> {}".format(func.parent, did))

        try:
            base_model = project.load_model(func.base_model)
        except IOError:
            raise DesignError("Base model {} does not appear to be valid".format(func.base_model))

        try:
            tmodel = func(base_model.copy(), project)
        except Exception as ex:
            raise DesignError("Error executing design function {} {}".format(did, ex))

        if not isinstance(tmodel, cobra.Model):
            raise DesignError("Design does not return a cobra Model instance")

        # We use the loaded model diff as the remaining patameters for the design
        # This is the only reason the model has to be loaded here
        diff = model_diff(base_model, tmodel)

        this = cls(
            did=did,
            name=func.name,
            description=func.description,
            project=project,
            parent=parent,
            base_model=func.base_model,
            conditions=func.conditions,
            is_pydesign=True,
            design_func=func,
            **diff
        )
        return this

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

        # Load parent design first
        if self.parent is not None:
            self.parent.add_to_model(mdl)

        mdl.design = self

        if self.is_pydesign:
            try:
                mdl = self.design_func(mdl, self.project)
            except Exception as ex:
                raise DesignError("Function execution error {}".format(ex))

            return mdl

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
        :param throw_exceptions: Throw json schema exceptions. If false, returns bool on any exception
        :return:
        """
        try:
            jsonschema.validate(design_dict, StrainDesign.design_schema)
        except (jsonschema.ValidationError, jsonschema.SchemaError) as exp:
            if throw_exceptions:
                raise exp
            return False
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
