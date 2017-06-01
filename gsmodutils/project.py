from __future__ import print_function, absolute_import
import os
import json
import glob
import cobra
from gsmodutils.model_diff import model_diff

class ProjectNotFound(Exception):
    pass


class ProjectConfigurationError(Exception):
    pass


class ProjectConfig(object):
    '''
    Class for configuration
    basically, takes configuration arguments and ensures that the required configuration options are included
    '''
    _required_cfg_params = [
            'description', 'author', 'author_email', 'models', 
            'repository_type', 'conditions_file', 'tests_dir',
            'design_dir'
        ]
    
    def __init__(self, **kwargs):
        
        loaded_cfg_params = [x.lower() for x in kwargs.keys()]
        # Check required options are there
        for it in self._required_cfg_params:
            if it not in loaded_cfg_params:
                raise ProjectConfigurationError('Project configuration option "{}" is missing'.format(it) )
        
        for arg, val in kwargs.items():
            setattr(self, arg.lower(), val)
            
        self._config_dict = kwargs
        

class GSMProject(object):
    '''
    Project class finds a gsmodutlils.json file in a given path and creates a project which allows a user to load:
        Models included within the project
        Designs that the model uses
    '''
    
    def __init__(self, path='.', **kwargs):
        # Load a project
        self._project_path = os.path.abspath(path)
        self.update()
    
    
    @property
    def _context_file(self):
        return os.path.join(self._project_path, '.gsmod_project.json')
    
    
    def _load_config(self, configuration):
        '''
        Sanatizes configuration input
        '''
        self.config = ProjectConfig(**configuration)
    
    
    def update(self):
        '''
        Updates this class from configuration file
        '''
        if not os.path.exists(self._project_path):
            
            raise ProjectNotFound('Project path {} does not exist'.format(self._project_path))
        
        if not os.path.exists(self._context_file):
            raise ProjectNotFound('Project settings file .gsmod_project in {} does not exist'.format(self._project_path))
        
        with open(self._context_file) as ctxfile:
            self.configuration = self._load_config(json.load(ctxfile))
        
        self._conditions_file = os.path.join(self.config.conditions_file)
        
        
    @property
    def conditions(self, update=False):
        '''
        Load the saved conditions file
        '''
        if update:
            self.update()
        with open(self._conditions_file) as cf:
            cdf = json.load(cf)
        return cdf
    
    
    @property
    def models(self):
        '''
        Lists all the models that can be loaded
        '''
        return self.config.models
    
    
    def load_model(self, mpath=None):
        '''
        Get a model stored by the project
        '''
        if mpath == None:
            mpath = self.config.models[0]
        
        if mpath not in self.config.models:
            raise IOError('Model file {} not found'.format(mpath))
        
        import cameo
        mdl = cameo.load_model(mpath)
        mdl._gsm_model_path = mpath
        return mdl
    
    
    @property
    def design_path(self):
        return os.path.join(self._project_path, self.config.design_dir)
    
    
    @property
    def designs(self):
        '''
        Return dictionary of all the designs stored for the project
        '''
        
        designs_s = dict()
        if design_dir is None:
             # All designs in the config specified design dir
             designs_direct = glob.glob(
                 os.path.join(self._project_path, self.config.design_dir, '*.json') )
             
        for dpath in designs_direct:
            with open(dpath) as dsgn_ctx_file:
                # TODO: validate design schema
                # if designs don't conform to schema, ignore them
                # maybe add option for throwing errors?
                designs_s[dpath] = json.load(dpath)
        
        return designs_s
    
    
    def load_design(self, design, conditions=None, model=None, copy=False):
        '''
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
        '''
        if type(model) in [str, unicode]:
            mdl = self.load_model()
        elif copy:
            mdl = model.copy()
        else:
            # TODO: type check model is actually a constraints based model (cameo/cobra)
            mdl = model
        
        designs = self.designs
        
        if type(design) is not dict:
            # just load a path
            if os.path.exists(design):
                # Design is a path
                design = json.load(design)
            
        
        # load specified conditions
        if conditions is not None:
            self.load_conditions(conditions, mdl, copy=False)
        
        # TODO: Check design conforms to valid scheme
        # Add new or changed metabolites to model
        for metabolite in  design['metabolites']:
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
                reaction.metabolites = rct['metabolites']
            
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
    
    
    def save_design(self, model, id, name, description='', conditions=None, base_model=None):
        '''
        Creates a design from a diff of model_a and model_b
        
        name
        description
        '''
        # Load either default model or model path
        if type(base_model) in [None, unicode, str]:
            base_model = self.load_model(mpath=base_model)
            self.load_conditions(conditions, base_model)
        
        if base_model is None:
            raise IOError('Base model not found')
    
        # Find all the differences between the models
        diff = model_diff(base_model, mdl)
        
        diff['description'] = description
        diff['id'] = id,
        diff['name'] = name
        diff['conditions'] = conditions
        diff['base_model'] = base_model.id
        
        design_save_path = os.path.join(design_path, '{}.json'.format(id))
        with open(design_save_path, 'w+') as dsp:
            json.dump(diff, dsp, indent=4)
        
    
    def load_conditions(self, conditions_id, model=None, copy=False):
        '''
        Load a model with a given set of pre-saved media conditions
        '''
        if model is None:
            mdl = self.load_model()
        elif copy:
            mdl = model.copy()
        
        conditions_store = self.conditions(update=True)
        mdl.load_medium(conditions_store[conditions_id])
        
        return mdl
        
    
    def add_conditions(self, model, conditions_id):
        '''
        Add media conditions that a given model has to the project
        '''
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
        conditions_store = self.conditions(update=True)
        conditions_store[conditions_id] = media
        with open(self._conditions_file, 'w+') as cf:
            json.dump(conditions_store, cf, indent=4)
        
        # TODO: mercurial commit