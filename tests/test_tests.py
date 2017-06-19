"""
Test cases for the GSMTests class and associated files
"""

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


class FakeProjectContext(object):
    
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

def test_json_tests():
    """"""
    with FakeProjectContext() as fp:
        # Create a fake json file with tests in it
        jtest = dict(
            test_1=dict(
                models=[],
                conditions=[],
                designs=[],
                reaction_fluxes=dict(
                    BIOMASS_Ec_iAF1260_core_59p81M=[0.72, 0.74]
                ),
                required_reactions=["DHQS"],
                description='TEST JSON TEST'
            )
        )
        
        project = GSMProject(fp.path)
        
        tpath = os.path.join(project.tests_dir, 'test_x.json')
        # write to project path
        json.dump(jtest, open(tpath, "w+"))
        # run test functions
        tester = project.project_tester()
        assert len(tester._d_tests) == 1
        tester._run_dtests()
        assert len(tester.load_errors) == 0

def test_py_tests():
    """
    This is a test of python test code within a python test.
    """
    
    code_str = """
def test_model():
    model = project.load_model()
    model.solve()
    """
    
    with FakeProjectContext() as fp:
        project = GSMProject(fp.path)
        tfp = os.path.join(project.tests_dir, 'test_x.py')
        
        with open(tfp, 'w+') as testf:
            testf.write(code_str)
            
        
        tester = project.project_tester()
        tester._py_tests()
    
