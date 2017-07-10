"""
Test cases for the GSMTests class and associated files
"""

from __future__ import print_function, absolute_import, division
from gsmodutils.project import GSMProject
import json
from tutils import FakeProjectContext
import os


def test_json_tests():
    """ Test the execution of json tests"""
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
        tester.collect_tests()
        assert len(tester.json_tests) == 1
        tester.run_all()
        assert len(tester.load_errors) == 0


def test_py_tests():
    """
    This is a test of python test code within a python test.
    
    These tests are important because the exec code is nasty to debug...
    """
    
    code_str = """
from gsmodutils.testutils import ModelTestSelector

@ModelTestSelector(models=[], conditions=[], designs=[])
def test_func(model, project, log):
    log.assertion(True, "Works", "Does not work", "Test")
    
def test_model(model, project, log):
    solution = model.solve()
    log.assertion(solution.f > 0.0, "Model grows", "Model does not grow")
    
    """
    
    with FakeProjectContext() as fp:
        project = GSMProject(fp.path)
        tfp = os.path.join(project.tests_dir, 'test_x.py')
        
        with open(tfp, 'w+') as testf:
            testf.write(code_str)
        
        tester = project.project_tester()
        tester.run_all()
        
        assert len(tester.syntax_errors) == 0
