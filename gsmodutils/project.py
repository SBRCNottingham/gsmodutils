from __future__ import print_function, absolute_import
import os
import json
import cameo


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
        
    
    def _load_conditions_file(self):
        with open(self._conditions_file) as ctxfile:
            self.conditions = json.load(ctxfile)
    
    
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
        
        self._conditions_file = os.path.join(self.configuration.conditions_file)
        
        self._load_conditions_file()
        
        
    @property
    def conditions(self, update=False):
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
        Get a model
        '''
        if mpath == None:
            mpath = self.config.models[0]
        
        if mpath not in self.config.models:
            raise IOError('Model file {} not found'.format(mpath))
        
        return cameo.load_model(mpath)
        
    
    @property
    def designs(self):
        '''
        Return dictionary of all the designs stored for the project
        '''
        pass
    
    
    def load_design(self, design, model=None, copy=False):
        '''
        Returns a model with a specified design modification
        
        Design must either be a design stored in the folder path or a path to a json file
        '''
        if type(model) in [str, unicode]:
            mdl = self.load_model()
        elif copy:
            mdl = model.copy()
        else:
            # TODO: type check model
            mdl = model
        
        designs = self.designs
        
        if type(design) is not dict:
            # just load a path
            if os.path.exists(design):
            # Desig
            design = json.load()
        
        # Check design conforms to valid scheme
        

    def save_design(self, model, name, base_model=None):
        '''
        Creates a design from a diff of model_a and model_b
        '''
        # Load either default model or model path
        if type(base_model) in [None, unicode, str]:
            base_model = self.load_model(mpath=base_model)
        
        if base_model is None:
            raise IOError('Base model not found')
    
    
    
    def load_conditions(self, condition_name, model=None, copy=False):
        '''
        '''
        pass
