from __future__ import print_function, absolute_import, division
import os
import json
import glob
import cobra

from gsmodutils.model_diff import model_diff
from gsmodutils.exceptions import ProjectNotFound, DesignError
from gsmodutils.project_config import ProjectConfig, default_project_file
from gsmodutils.tester import GSMTester

from cobra.exceptions import Infeasible
from lockfile import LockFile
from cameo.core.utils import load_medium


class GSMProject(object):
    """
    Project class finds a gsmodutlils.json file in a given path and creates a project which allows a user to load:
        Models included within the project
        Designs that the model uses
    """
    def __init__(self, path='.'):
        """Load a project"""
        self._project_path = os.path.abspath(path)
        self._loaded_model = None
        self.update()
        self._conditions_file = os.path.join(self._project_path, self.config.conditions_file)

    @property
    def project_path(self):
        return self._project_path

    @property
    def _context_file(self):
        return os.path.join(self._project_path, default_project_file)

    def _load_config(self, configuration):
        """
        Sanatizes configuration input
        """
        self.config = ProjectConfig(**configuration)

    @property
    def tests_dir(self):
        """ Tests directory """
        return os.path.join(self._project_path, self.config.tests_dir)

    def project_tester(self):
        """Creates a tester for this project instance"""
        return GSMTester(self)

    @property
    def _project_context_lock(self):
        """
        Returns a gloab project lock to stop multiple operations on files.
        This software is not designed to be used in multiple user environments, so this is slow. However, it provides
        some degree of protection for the user against modifying the same files
        """
        lock_path = os.path.join(self._project_path, '.gsmodultils_project_lock')
        return LockFile(lock_path)

    def update(self):
        """
        Updates this class from configuration file
        """
        if not os.path.exists(self._project_path):
            
            raise ProjectNotFound('Project path {} does not exist'.format(self._project_path))
        
        if not os.path.exists(self._context_file):
            raise ProjectNotFound(
                'Project settings file {} in {} does not exist'.format(default_project_file, self._project_path))
        
        with open(self._context_file) as ctxfile:
            self._load_config(json.load(ctxfile))

        self._conditions_file = os.path.join(self._project_path, self.config.conditions_file)

    def get_conditions(self, update=False):
        """
        Load the saved conditions file
        """
        if update:
            self.update()
            
        with open(self._conditions_file) as cf:
            cdf = json.load(cf)
        return cdf
    
    @property
    def conditions(self):
        return self.get_conditions()

    def iter_models(self):
        """
        Generator for models
        """
        for mdl_path in self.config.models:
            yield self.load_model(mpath=mdl_path)

    @property
    def models(self):
        """
        Lists all the models that can be loaded
        """
        return list(self.iter_models())

    def load_model(self, mpath=None):
        """
        Get a model stored by the project
        mpath refers to the relative path of the model
        """
        if mpath is None:
            mpath = self.config.default_model
        
        if mpath not in self.config.models:
            raise IOError('Model file {} not found in project, maybe you need to add it'.format(mpath))
        
        import cameo
        
        load_path = os.path.join(self._project_path, mpath)
        mdl = cameo.load_model(load_path)
        mdl._gsm_model_path = mpath
        return mdl

    @property
    def model(self):
        """
        Returns default model for project
        """
        if self._loaded_model is None:
            self._loaded_model = self.load_model()
            
        return self._loaded_model

    def add_model(self, model_path, validate=True):
        """
        Add a model given a path to it copy it to model directory unless its in the project path already.
        """
        if not os.path.exists(model_path):
            raise IOError('No such model {}'.format(model_path))

        model_path = os.path.abspath(model_path)

        if validate:
            pass  # TODO validate models

        # check model isn't in the project already
        npath = os.path.basename(model_path)
        if npath in self.config.models:
            raise KeyError('Model of the same name already included in project')

        # add model to project and save configuration
        self.config.models.append(npath)
        self.config.save_config(self.project_path)

    @property
    def design_path(self):
        return os.path.join(self._project_path, self.config.design_dir)

    @property
    def designs(self):
        """
        Return list of all the designs stored for the project
        """
        designs_s = dict()
        
        # All designs in the config specified design dir
        designs_direct = glob.glob(
            os.path.join(self._project_path, self.config.design_dir, '*.json'))
             
        for dpath in designs_direct:
            with open(dpath) as dsgn_ctx_file:
                d_id = os.path.basename(dpath).split(".json")[0]
                ft = json.load(dsgn_ctx_file)
                # if designs don't conform to schema, ignore them
                if self._validate_design(ft):
                    designs_s[d_id] = ft

        return designs_s

    @staticmethod
    def _validate_design(ft):
        """ validates design dictionaries for required fields"""
        required_fields = ["id", "name", "description", "metabolites", "reactions", "genes"]
        for field in required_fields:
            if field not in ft:
                return False

        return True

    @property
    def list_designs(self, valid=False):
        designs_direct = glob.glob(
            os.path.join(self._project_path, self.config.design_dir, '*.json'))

        if valid:
            n_direct = []
            for dpath in designs_direct:
                with open(dpath) as dsgn_ctx_file:
                    ft = json.load(dsgn_ctx_file)
                    if self._validate_design(ft):
                        n_direct.append(dpath)

            designs_direct = n_direct

        return [os.path.basename(dpath).split(".json")[0] for dpath in designs_direct]
    
    def _construct_design(self, design_id):
        """
        Loads an existing design
        """
        if design_id not in self.list_designs:
            raise KeyError('Design {} not found'.format(design_id))
        
        des_path = os.path.join(self._project_path, self.config.design_dir, '{}.json'.format(design_id))
    
        with open(des_path) as dsn_ctx:
            design_dict = json.load(dsn_ctx)
        
        return design_dict
    
    def load_design(self, design, model=None, copy=False, parent_stack=None):
        """
        Returns a model with a specified design modification
        
        Design must either be a design stored in the folder path or a path to a json file
        The json file should conform to the same standard as a json model
        
        required fields:
            "metabolites":[]
            "reactions":[]
            "description": "", 
            "notes": {}, 
            "genes": [], 
            "id":""
        
        optional fields:
            "parent": str - parent design to be applied first
            "conditions": ""
            "removed_reactions":[]
            "removed_metabolites":[]
        
        Note if conditions is specified it is loaded first
        other bounds are set afterwards
        """

        if parent_stack is None:
            parent_stack = []

        if type(design) is not dict:
            if design in self.list_designs:
                design = self._construct_design(design)
            # just load a path
            elif os.path.exists(design):
                # Design is a path
                with open(design) as dfctx:
                    design = json.load(dfctx)
            elif len(parent_stack):
                raise DesignError('Parent design {} does not exist.'.format(parent_stack[-1]))
            else:
                raise IOError('Design {} not found.'.format(design))

        if 'parent' in design and design['parent'] not in [None, '']:
            if type(design['parent']) is not str:
                raise DesignError('Parent design must be a string identifier.')

            if design['parent'] in parent_stack:
                raise DesignError('Cyclic behaviour detected in parental design. Consider running a project clean.')

            parent_stack += [design['parent']]
            mdl = self.load_design(design['parent'], model=model, copy=copy, parent_stack=parent_stack)
        elif type(model) in [type(None), str, unicode]:
            mdl = self.load_model(mpath=model)
            # TODO: type check model is actually a constraints based model (cameo/cobra)
        elif copy:
            mdl = model.copy()
        else:
            # TODO: type check model is actually a constraints based model (cameo/cobra)
            mdl = model

        # load specified conditions
        if 'conditions' in design and design['conditions'] is not None:
            self.load_conditions(design['conditions'], mdl, copy=False)
        
        # TODO: Check design conforms to valid scheme
        # Add new or changed metabolites to model
        for metabolite in design['metabolites']:
            # create new metabolite object if its not in the model already
            if metabolite['id'] in mdl.metabolites:
                metab = mdl.metabolites.get_by_id(metabolite['id'])
            else:
                metab = cobra.Metabolite()
            
            # Note that we don't check any of these properties, just update them
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
        for rct in design['reactions']:
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

            metabolites = dict([(str(x), v) for x, v in rct['metabolites'].items()])  # fixes bug in cobra with unicode

            reaction.add_metabolites(metabolites)
            reaction.objective_coefficient = rct['objective_coefficient']

        # delete removed metabolites/reactions
        if 'removed_reactions' in design:
            for rtid in design['removed_reactions']:
                try:
                    reaction = mdl.reactions.get_by_id(rtid)
                    reaction.remove_from_model()
                except KeyError:
                    pass
        
        if 'removed_metabolites' in design:
            for metid in design['removed_metabolites']:
                try:
                    met = mdl.metabolites.get_by_id(metid)
                    met.remove_from_model()
                except KeyError:
                    pass
        mdl.id += ":design_{}".format(design["id"])
        return mdl
    
    def save_design(self, model, did, name, description='', conditions=None, base_model=None, parent=None,
                    overwrite=False):
        """
        Creates a design from a diff of model_a and model_b
        
        id should be a string with no spaces (conversion handled)
        
        Returns the saved design diff

        :param model: cobrapy/cameo model
        :param did: design identifier
        :param name: name of the design
        :param description: text description of what it does
        :param conditions: conditions that should be applied for the design
        :param base_model: Model that the design should be derived from - specified model included in project
        :param parent: string for parent design that this design is a diff from
        :param overwrite: overwrite and existing design (only applies if the id is already in use)
        """
        # Test, infeasible designs should not be added
        status = model.solver.optimize()
        if status == 'infeasible':
            raise Infeasible('Could not find valid solution')

        if parent is not None and parent not in self.designs:
            # check that the parent design actually exists
            raise DesignError('specified parent not found')

        did = str(did).replace(' ', '_')
        design_save_path = os.path.join(self.design_path, '{}.json'.format(did))

        if os.path.exists(design_save_path) and not overwrite:
            raise IOError('File {} exists'.format(design_save_path))

        # Load either default model or model path
        if type(base_model) in [type(None), unicode, str] and parent is None:
            base_model = self.load_model(mpath=base_model)
            if conditions is not None:
                self.load_conditions(conditions, base_model)
        elif parent is not None:
            # If a parent design is specified this model is loaded first
            base_model = self.load_design(parent)
        
        if base_model is None:
            raise IOError('Base model not found')
        
        # Find all the differences between the models
        diff = model_diff(base_model, model)
        
        diff['description'] = description
        diff['id'] = did,
        diff['name'] = name
        diff['conditions'] = conditions
        diff['base_model'] = base_model.id
        diff['parent'] = parent

        with open(design_save_path, 'w+') as dsp:
            json.dump(diff, dsp, indent=4)
        
        return diff
    
    def load_conditions(self, conditions_id, model=None, copy=False):
        """
        Load a model with a given set of pre-saved media conditions
        :param conditions_id: identifier of conditions file
        :param model: string or cobrapy/cameo model
        :param copy: return copy of model or modify inplace
        :return:
        """
        if model is None or type(model) is str:
            mdl = self.load_model(model)
        elif copy:
            mdl = model.copy()
        else:
            mdl = model
        
        conditions_store = self.get_conditions(update=True)

        cx = conditions_store['growth_conditions'][conditions_id]
        load_medium(mdl, cx['media'])
        if "carbon_source" in cx and cx["carbon_source"] is not None:
            # Will throw error if invalid transporter
            c_tx = mdl.reactions.get_by_id(cx["carbon_source"])
            c_tx.upper_bound = c_tx.lower_bound

        return mdl

    def growth_condition(self, conditions_id):
        conditions_store = self.get_conditions(update=True)
        return conditions_store['growth_conditions'][conditions_id]['observe_growth']

    def save_conditions(self, model, conditions_id, carbon_source=None, apply_to=None, observe_growth=True):
        """
        Add media conditions that a given model has to the project. Essentially the lower bounds on transport reactions.
        All other trnasport reactions will be switched off.

        In some cases, one may wish to set conditions under which a model should not grow.
        observe_growth allows this to be configured. If using a single model or if the condition should not grow under
        any circumstances, observe_growth can be set to false.

        If certain models should grow, specify this with a a tuple where the entries refer to the model files tracked by
        the project. All models specified must be contained within the project.

        :param model: cobrapy or cameo model
        :param conditions_id: identifier for the conditions should be unique
        :param carbon_source: name of carbon source in the media that has a fixed uptake rate
        if None this just becomes a lower bound
        :param apply_to: iterable of models that this set of conditions applies to
        :param observe_growth: bool or list.
        :return:
        """
        # If it can't get a solution then this will raise errors.
        status = model.solver.optimize()
        if not observe_growth and status != 'infeasible':
            raise AssertionError('Model should not grow')
        elif observe_growth and status == 'infeasible':
            raise Infeasible('Cannot find valid solution - should conditions result in growth?')

        if apply_to is None:
            apply_to = []
        else:
            if type(apply_to) is not list:
                apply_to = [apply_to]

            for mdl_path in apply_to:
                if mdl_path not in self.config.models:
                    raise KeyError("Model {} not in current project".format(mdl_path))

        # List all transport reactions in to the cell
        def is_exchange(rr):
            return (len(rr.reactants) == 0 or len(rr.products) == 0) and len(rr.metabolites) == 1

        def is_media(rr):
            if rr.lower_bound < 0 and is_exchange(rr):
                return True
            return False
        
        media = {}
        for r in model.reactions:
            if is_media(r):
                media[r.id] = r.lower_bound
        
        # save to conditions file
        conditions_store = self.get_conditions(update=True)

        if carbon_source not in media:
            raise KeyError("carbon source not valid")

        conditions_store['growth_conditions'][conditions_id] = dict(
            media=media,
            models=apply_to,
            observe_growth=observe_growth,
            carbon_source=carbon_source,
        )
        self._write_conditions(conditions_store)

    def _write_conditions(self, conditions_store):
        """
        Writes updated conditions store
        TODO: Validate passed dictionary
        TODO: make this a persistent dict stored in memory?
        :param conditions_store:
        :return:
        """
        with self._project_context_lock:
            with open(self._conditions_file, 'w+') as cf:
                json.dump(conditions_store, cf, indent=4)

    def clean_project(self, auto_remove=False):
        """
        Check all design and condition settings to see if they contain orphans or links to non-existing models
        If auto_remove is true applied, any orphan files are automatically deleted and entries to missing models are
        also removed.
        :return: tuple(list, list) of all orphan designs and conditions (ones removed if auto_remove is set to true)
        """
        # TODO: remove bad designs
        with self._project_context_lock:
            bad_entries = []
            models = self.config.models
            conditions_store = self.conditions
            for ck, conditions in conditions_store['growth_conditions'].items():
                # check all models
                for mdl in conditions['models']:
                    if mdl not in models:
                        bad_entries.append(mdl)

                        # delete the conditions file
                        if auto_remove and len(bad_entries) == len(conditions['models'])\
                                and len(conditions['models']) > 0:
                            del conditions_store[ck]
                            self._write_conditions(conditions_store)
                        elif auto_remove and len(bad_entries):
                            conditions['models'] = [x for x in conditions['models'] if x not in bad_entries]
                            self._write_conditions(conditions_store)
