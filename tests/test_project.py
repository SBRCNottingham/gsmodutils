'''
Tests for GSMProject class

TODO: tests for command line interface
'''


from __future__ import print_function, absolute_import, division
import pytest
from gsmodutils.exceptions import ProjectConfigurationError
from gsmodutils.project import GSMProject
from gsmodutils.project_config import ProjectConfig
from gsmodutils.project_config import _default_model_conditionsfp, _default_project_file
import cameo
import cobra
import os
import shutil
import json
import hglib
import tempfile


class FakeProjectContext():
    
    def __init__(self):
        '''
        Assumes projectConfig class works correctly
        '''
        self.path = tempfile.mkdtemp()
        self.mdl_path = tempfile.mkstemp()


    def __enter__(self):
        '''
        Create a temporary gsmodutils project folder
        '''
        self.model = cameo.models.bigg.iAF1260
        cobra.io.save_json_model(self.model, self.mdl_path[1])
        add_models = [self.mdl_path[1]]
        configuration = dict(
                description='TEST PROJECT ONLY',
                author='test',
                author_email='123@abc.com',
                default_model=None,
                models=[],
                repository_type='hg',
                conditions_file=_default_model_conditionsfp,
                tests_dir='tests',
                design_dir='designs'
        )
        
        self.cfg = ProjectConfig(**configuration)
        self.cfg.create_project(self.path, addmodels=add_models)
        return self
        
    
    def __exit__(self, *args):
        '''
        Delete directory and model
        '''
        shutil.rmtree(self.path)
        os.remove(self.mdl_path[1])
        

def test_load_project():
    
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        assert project._project_path == ctx.path
        

def test_create_design():
    '''
    Create a design that adds and removes reactions
    '''
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        model = project.model
        model.reactions.ATPM.lower_bound = 8.0
        # Modified metabolite
        model.metabolites.h2o_c.formula = 'H202'
        # Remove a reaction
        model.reactions.UDPGD.remove_from_model()

        # Add a reaction with a hetrologous metabolite
        # Add transporter for hetrologous metabolit
        project.save_design(model, 'test_design', 'test design 01', 'This is a test')
    
        # assert design has been saved 
        assert 'test_design' in project.list_designs
        assert os.path.exists(os.path.join(ctx.path, 'designs', 'test_design.json'))
        
        # Test loading the design into the default model
        nmodel = project.load_design('test_design')
        # assert that the reaction is removed 
        # assert that the metabolite is changed
        assert nmodel.metabolites.h2o_c.formula == 'H202'
        
        # assert that the reaction bounds have been modified
        assert nmodel.reactions.ATPM.lower_bound == 8.0
        
        
def test_load_conditions():
    pass


