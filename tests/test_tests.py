"""
Test cases for the GSMTests class and associated files
"""
from gsmodutils import GSMProject

import json
from tutils import FakeProjectContext
import os
import pytest
from cobra.exceptions import Infeasible
from cameo.core.utils import load_medium
from click.testing import CliRunner
import gsmodutils.cli


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
        runner = CliRunner()
        result = runner.invoke(gsmodutils.cli.test, ['--project_path', fp.path, '--verbose'])
        assert result.exit_code == 0


def test_py_tests():
    """
    This is a test of python test code within a python test.
    
    These tests are important because the exec code is nasty to debug...
    """
    
    code_str = """
# Look our tests are python 2 compatible!
# p.s. if you're reading this you're such a nerd
from __future__ import print_function 
from gsmodutils.test.utils import ModelTestSelector

@ModelTestSelector(models=[], conditions=[], designs=[])
def test_func(model, project, log):
    log.assertion(True, "Works", "Does not work", "Test")
    
def test_model(model, project, log):
    solution = model.solver.optimize()
    print('This is the end')
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

        runner = CliRunner()
        result = runner.invoke(gsmodutils.cli.test, ['--project_path', fp.path, '--verbose'])
        assert result.exit_code == 0


def test_conditions():
    with FakeProjectContext() as fp:
        # add some growth conditions
        conditions = dict(
            EX_xyl__D_e=-8.0,
            EX_ca2_e=-99999.0,
            EX_cbl1_e=-0.01,
            EX_cl_e=-99999.0,
            EX_co2_e=-99999.0,
            EX_cobalt2_e=-99999.0,
            EX_cu2_e=-99999.0,
            EX_fe2_e=-99999.0,
            EX_fe3_e=-99999.0,
            EX_h2o_e=-99999.0,
            EX_h_e=-99999.0,
            EX_k_e=-99999.0,
            EX_mg2_e=-99999.0,
            EX_mn2_e=-99999.0,
            EX_mobd_e=-99999.0,
            EX_na1_e=-99999.0,
            EX_nh4_e=-99999.0,
            EX_o2_e=-18.5,
            EX_pi_e=-99999.0,
            EX_so4_e=-99999.0,
            EX_tungs_e=-99999.0,
            EX_zn2_e=-99999.0
        )
        mdl = fp.project.model
        load_medium(mdl, conditions)
        mdl.solver.optimize()
        fp.project.save_conditions(mdl, "xyl_src", apply_to=fp.project.config.default_model)

        load_medium(mdl, dict())
        fp.project.save_conditions(mdl, "bad", apply_to=fp.project.config.default_model, observe_growth=False)

        # Shouldn't allow conditions that don't grow without being formally specified
        with pytest.raises(Infeasible):
            fp.project.save_conditions(mdl, "very bad", apply_to=fp.project.config.default_model)

        assert(len(fp.project.get_conditions(update=True)['growth_conditions']) == 2)
        # run the default test
        tester = fp.project.project_tester()
        tester.collect_tests()
        assert(len(tester.default_tests) == 3)

        tester.run_all()

        # Test the cli interface
        runner = CliRunner()
        result = runner.invoke(gsmodutils.cli.test, ['--project_path', fp.path, '--verbose'])
        assert result.exit_code == 0