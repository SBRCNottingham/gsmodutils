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
        
        self._conditions_file = os.path.join(self.configuration)
        
        
    @property
    def conditions(self):
        # self.update() # TODO: profile always updating before loading properties
        with open(self._conditions_file) as cf:
            cdf = json.load(cf)
        return cdf
    
    
    @property
    def models(self):
        '''
        Lists all the models that can be loaded
        '''
        return self.config.models
    
    
    def get_model(self, mpath=None):
        '''
        Get the model
        '''
        pass
    
    
    def get_designs(self):
        '''
        Return dictionary of all the designs of the model
        '''
        pass
    
    
    def load_design(self, design):
        '''
        Returns a model with a specified design modification
        '''
        pass


    def save_design(self, model, name, base_model=None):
        '''
        Creates a design from a diff of model_a and model_b
        '''
        pass
    
    
    def load_conditions(self, condition_name, model=None, copy=False):
        '''
        '''
        pass
