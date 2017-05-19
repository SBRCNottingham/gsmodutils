import os
import json
import cameo

class ProjectNotFound(Exception):
    pass


class Project(object):
    '''
    Project class finds a gsmodutlils.json file in a given path and creates a project which allows a user to load:
        Models included within the project
        Designs that the model uses
    '''
    
    def __init__(self, **kwargs):
        pass
    
    
    def update(self):
        '''
        Updates this class
        '''
        pass
    
    
    def models(self):
        '''
        Lists all the models that can be loaded
        '''
        pass
    
    
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
    
    
    def get_conditions(self):
        '''
        List the available model conditions
        '''
        pass
    
    
    def load_conditions(self, condition_name, model=None, copy=False):
        '''
        '''
        pass