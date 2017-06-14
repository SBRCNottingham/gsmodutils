from __future__ import print_function, absolute_import, division
import os
import json
import glob
import cobra
import hglib
import shutil

from gsmodutils.model_diff import model_diff
from gsmodutils.exceptions import ProjectConfigurationError, ProjectNotFound
from gsmodutils.project_config import ProjectConfig, _default_project_file, _default_model_conditionsfp


class GSMProject(object):
    """
    Project class finds a gsmodutlils.json file in a given path and creates a project which allows a user to load:
        Models included within the project
        Designs that the model uses
    """
    
    def __init__(self, path='.', **kwargs):
        # Load a project
        self._project_path = os.path.abspath(path)
        self._loaded_model = None
        self.update()
    
    @property
    def _context_file(self):
        return os.path.join(self._project_path, _default_project_file)

    def _load_config(self, configuration):
        """
        Sanatizes configuration input
        """
        self.config = ProjectConfig(**configuration)

    @property
    def tests_dir(self):
        """ Tests directory """
        return os.path.join(self._project_path, self.config.tests_dir)

    def update(self):
        """
        Updates this class from configuration file
        """
        if not os.path.exists(self._project_path):
            
            raise ProjectNotFound('Project path {} does not exist'.format(self._project_path))
        
        if not os.path.exists(self._context_file):
            raise ProjectNotFound(
                'Project settings file {} in {} does not exist'.format(_default_project_file, self._project_path))
        
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
    
    def add_model(self, model_path):
        """
        Add a model given a path to it (copy it to model directory unless its in the project path already.
        """
        pass

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
            os.path.join(self._project_path, self.config.design_dir, '*.json') )
             
        for dpath in designs_direct:
            with open(dpath) as dsgn_ctx_file:
                # TODO: validate design schema
                # if designs don't conform to schema, ignore them
                # maybe add option for throwing errors?
                d_id = os.path.basename(dpath).split(".json")[0]
                designs_s[d_id] = json.load(dsgn_ctx_file)
        
        return designs_s
    
    @property
    def list_designs(self):
        designs_direct = glob.glob(
            os.path.join(self._project_path, self.config.design_dir, '*.json') )
        
        return [os.path.basename(dpath).split(".json")[0] for dpath in designs_direct]
    
    def _construct_design(self, design_id):
        """
        Loads an existing design
        """
        if design_id not in self.list_designs:
            raise KeyError('Design {} not found'.format(design_id) )
        
        des_path = os.path.join(self._project_path, self.config.design_dir, '{}.json'.format(design_id) )
    
        with open(des_path) as dsn_ctx:
            design_dict = json.load(dsn_ctx)
        
        return design_dict
    
    def load_design(self, design, model=None, copy=False):
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
            "conditions": ""
            "removed_reactions":[]
            "removed_metabolites":[]
        
        Note if conditions is specified it is loaded first
        other bounds are set afterwards
        """
        if type(model) in [type(None), str, unicode]:
            mdl = self.load_model(mpath=model)
            # TODO: type check model is actually a constraints based model (cameo/cobra)
        elif copy:
            mdl = model.copy()
        else:
            # TODO: type check model is actually a constraints based model (cameo/cobra)
            mdl = model

        if type(design) is not dict:
            
            if design in self.list_designs:
                design = self._construct_design(design)
            # just load a path
            elif os.path.exists(design):
                # Design is a path
                with open(design) as dfctx:
                    design = json.load(dfctx)
            else:
                raise IOError('design not found')

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
                mdl.add_metabolite(metab)  
                
        # Add new or changed reactions to model
        for rct in design['reactions']:
            if rct['id'] in mdl.reactions:
                reaction = mdl.reactions.get_by_id(rct['id'])
                reaction.clear_metabolites()
                reaction.add_metabolites(rct['metabolites'])
            else:
                reaction = cobra.Reaction()
                reaction.id = rct['id']

            reaction.name = rct['name']
            reaction.lower_bound = rct['lower_bound']
            reaction.upper_bound = rct['upper_bound']
            reaction.objective_coefficient = rct['objective_coefficient']
            reaction.gene_reaction_rule = rct['gene_reaction_rule']
            reaction.subsystem = rct['subsystem']
            reaction.name = rct['name']
            reaction.variable_kind = rct['variable_kind']

            if rct['id'] not in mdl.reactions:
                mdl.add_reaction(reaction)
                reaction = mdl.reactions.get_by_id(reaction.id)
                reaction.add_metabolites(rct['metabolites'])
            
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

        return mdl
    
    def save_design(self, model, id, name, description='', conditions=None, base_model=None, overwrite=False):
        """
        Creates a design from a diff of model_a and model_b
        
        id should be a string with no spaces (conversion handled)
        
        Returns the saved design diff
        
        name
        description
        """
        # Test, infesible designs should not be added
        model.solve()
        
        id = unicode(id).replace(' ', '_')
        
        # Load either default model or model path
        if type(base_model) in [type(None), unicode, str]:
            base_model = self.load_model(mpath=base_model)
            if conditions is not None:
                self.load_conditions(conditions, base_model)
        
        if base_model is None:
            raise IOError('Base model not found')
        
        # Find all the differences between the models
        diff = model_diff(base_model, model)
        
        diff['description'] = description
        diff['id'] = id,
        diff['name'] = name
        diff['conditions'] = conditions
        diff['base_model'] = base_model.id
        
        design_save_path = os.path.join(self.design_path, '{}.json'.format(id))
        with open(design_save_path, 'w+') as dsp:
            json.dump(diff, dsp, indent=4)
        
        # TODO: adding to mercurial repository
        
        return diff
    
    def load_conditions(self, conditions_id, model=None, copy=False):
        """
        Load a model with a given set of pre-saved media conditions
        """
        if model is None:
            mdl = self.load_model()
        elif copy:
            mdl = model.copy()
        else:
            mdl = model
        
        conditions_store = self.get_conditions(update=True)
        mdl.load_medium(conditions_store[conditions_id])
        
        return mdl
    
    def save_conditions(self, model, conditions_id):
        """
        Add media conditions that a given model has to the project
        """
        # If it can't get a solution then this will raise errors.
        model.solve()
        
        # List all transport reactions in to the cell
        def is_exchange(r):
            return (len(r.reactants) == 0 or len(r.products) == 0) and len(r.metabolites) == 1

        def is_media(r):
            if r.lower_bound < 0 and is_exchange(r):
                return True
            return False
        
        media = {}
        for r in model.reactions:
            if is_media(r):
                media[r.id] = r.lower_bound
        
        # save to conditions file
        conditions_store = self.get_conditions(update=True)
        conditions_store[conditions_id] = media
        with open(self._conditions_file, 'w+') as cf:
            json.dump(conditions_store, cf, indent=4)
        
        # TODO: mercurial commit
