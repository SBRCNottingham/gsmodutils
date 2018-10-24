"""
Test cases for the GSMTests class and associated files
"""
from __future__ import print_function
from gsmodutils import GSMProject
from gsmodutils.project.design import StrainDesign
from gsmodutils.test.tester import GSMTester
from gsmodutils.test.utils import ModelLoader, ResultRecord
import json
from tutils import FakeProjectContext
import os
import pytest
from cobra.exceptions import Infeasible
from gsmodutils.utils.io import load_medium
from click.testing import CliRunner
import gsmodutils.cli
from gsmodutils.test.utils import stdout_ctx
from six import exec_


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
        with open(tpath, "w+") as ff:
            json.dump(jtest, ff)

        jtest = dict(
            test_1=dict(
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

        tpath = os.path.join(project.tests_dir, 'test_invalid.json')
        # write to project path
        with open(tpath, "w+") as ff:
            json.dump(jtest, ff)

        tpath = os.path.join(project.tests_dir, 'test_load_error.json')
        with open(tpath, 'w+') as tt:
            tt.write('not json\n')

        # run test functions
        tester = project.project_tester()
        tester.collect_tests()
        assert len(tester.json_tests) == 1
        tester.run_all()
        assert len(tester.load_errors) == 1
        assert len(tester.invalid_tests) == 1

        runner = CliRunner()
        result = runner.invoke(gsmodutils.cli.test, ['--project_path', fp.path, '--verbose'])
        assert result.exit_code == 0

        result = runner.invoke(gsmodutils.cli.test,
                               ['--project_path', fp.path, '--verbose', '--test_id', 'test_x.json'])

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

@ModelTestSelector(models=["not_there"], conditions=["xyl_src", "bad", "not_there"], designs=["not_there"])
def test_func(model, project, log):
    log.assertion(True, "Works", "Does not work", "Test")


# For code coverage
@ModelTestSelector()
def test_func_cove(model, project, log):
    log.assertion(True, "Works", "Does not work", "Test")


def test_model(model, project, log):
    solution = model.solver.optimize()
    print('This is the end')
    log.warning(True, "this is a warning")
    log.assertion(True, "Model grows", "Model does not grow")
    log.assertion(False, "Model grows", "Model does not grow")
    
    
def test_exception(model, project, log):
    raise Exception('This is exceptional')
    """

    syntax_err = """
def test_model(model, project, log):
    print('This is the end {}'.format(solution)
    """

    with FakeProjectContext() as fp:
        project = GSMProject(fp.path)

        fp.add_fake_conditions()
        mdl = fp.project.model
        load_medium(mdl, dict())
        fp.project.save_conditions(mdl, "bad", apply_to=fp.project.config.default_model, observe_growth=False)

        test_codep = 'test_code.py'
        tfp = os.path.join(project.tests_dir, test_codep)
        
        with open(tfp, 'w+') as testf:
            testf.write(code_str)

        tfp = os.path.join(project.tests_dir, 'test_syn_err.py')

        with open(tfp, 'w+') as testf:
            testf.write(syntax_err)

        tester = project.project_tester()
        tester.run_all()
        
        assert len(tester.syntax_errors) == 1

        log = tester.run_by_id('test_code.py::test_model')
        assert log.std_out == "This is the end\n"  # Test record should capture the standard output

        runner = CliRunner()
        lpath = os.path.join(fp.path, 'lp.json')
        result = runner.invoke(gsmodutils.cli.test, ['--project_path', fp.path, '--verbose', '--log_path', lpath])
        assert result.exit_code == 0

        result = runner.invoke(gsmodutils.cli.test,
                               ['--project_path', fp.path, '--verbose', '--test_id', test_codep])

        assert result.exit_code == 0
        result = runner.invoke(gsmodutils.cli.test,
                               ['--project_path', fp.path, '--verbose',
                                '--test_id', '{}::test_func'.format(test_codep)])

        assert result.exit_code == 0

        result = runner.invoke(gsmodutils.cli.test,
                               ['--project_path', fp.path, '--verbose', '--test_id', 'test_syn_err.py'])

        assert result.exit_code == -1

        project.run_tests()


def test_conditions():
    with FakeProjectContext() as fp:
        # add some growth conditions
        fp.add_fake_conditions()
        mdl = fp.project.model
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


def test_tester():
    """ Test the tester in test tests """
    with pytest.raises(TypeError):
        # Shouldn't load
        GSMTester(None)


def test_essential_pathways():
    """
    Test adding of json test utility
    reactions, description = '', reaction_fluxes = None,
    models = None, designs = None, conditions = None, overwrite = False
    """
    with FakeProjectContext() as fp:
        fp.add_fake_conditions()
        fp.add_fake_designs()

        reactions = ['PYK']
        # Test a model
        fp.project.add_essential_pathway('model_test', reactions=reactions)

        with pytest.raises(IOError):
            fp.project.add_essential_pathway('model_test', reactions=reactions)

        # Add an essential pathway test for a design only
        fp.project.add_essential_pathway('design_test', reactions=reactions, designs=['mevalonate_cbb'])
        # Test conditions
        fp.project.add_essential_pathway('conditions_test', reactions=reactions, conditions=['xyl_src'])

        assert os.path.exists(os.path.join(fp.project.tests_dir, 'test_model_test.json'))
        assert os.path.exists(os.path.join(fp.project.tests_dir, 'test_design_test.json'))
        assert os.path.exists(os.path.join(fp.project.tests_dir, 'test_conditions_test.json'))

        # Test conditions designs and
        tester = fp.project.project_tester()
        tester.run_all()


def test_std_out_capture():
    """ Test the context manager for capturing standard output by python tests """
    output_message = "foooo"
    with stdout_ctx() as context:
        print(output_message)
    assert context.getvalue() == output_message+"\n"


def test_std_out_capture_in_exec():
    """ Test the context manager for capturing standard output by python tests inside a string executed function """
    output_message = "foooo"

    exec_code = 'print("{}")'.format(output_message)

    with stdout_ctx() as context:
        compiled_code = compile(exec_code, '', 'exec')
        exec_(compiled_code, {})

    assert context.getvalue() == output_message+"\n"


def test_model_loader():
    """ Model loader utility tests """
    with FakeProjectContext(use_second_model=True) as ctx:
        ml = ModelLoader(ctx.project, "e_coli_core.json", None, None)
        ctx.add_fake_conditions()
        log = ResultRecord("TL")
        model = ml.load(log)
        assert os.path.basename(model.mpath) == "e_coli_core.json"
        assert model.design is None

        ctx.add_fake_designs()
        ml = ModelLoader(ctx.project, None, "xyl_src", "mevalonate_cbb")
        log = ResultRecord("TL2")
        model = ml.load(log)
        treac = model.reactions.get_by_id("EX_xyl__D_e")
        assert isinstance(model.design, StrainDesign)
        assert model.design.id == "mevalonate_cbb"
        assert treac.lower_bound == -8.0

        ml = ModelLoader(ctx.project, None, "xyl_src", None)
        log = ResultRecord("TL2")
        model = ml.load(log)
        treac = model.reactions.get_by_id("EX_xyl__D_e")
        assert treac.lower_bound == -8.0


def test_model_tests():
    code_str = """
# Look our tests are python 2 compatible!
# p.s. if you're reading this you're such a nerd
from __future__ import print_function 
from gsmodutils.test.utils import ModelTestSelector

@ModelTestSelector(designs=["mevalonate_cbb"])
def test_funcdes(model, project, log):
    log.assertion(False, "Works", "Does not work", "Test1")
    
@ModelTestSelector(conditions=["xyl_src"])
def test_func(model, project, log):
    log.assertion(True, "Works", "Does not work", "Test2")
        """

    with FakeProjectContext(use_second_model=True) as ctx:
        ctx.add_fake_conditions()
        ctx.add_fake_designs()

        test_codep = 'test_code.py'
        tfp = os.path.join(ctx.project.tests_dir, test_codep)

        with open(tfp, "w+") as codef:
            codef.write(code_str)

        # Test a design
        design = ctx.project.load_design("mevalonate_cbb")
        testsdes = design.run_tests()
        assert len(testsdes) == 2
        assert not testsdes["test_code.py::test_funcdes::iAF1260.json::mevalonate_cbb"].log.is_success

        # Test a model
        model = ctx.project.load_model()
        tests = model.run_tests()
        assert len(tests) == 3
        assert tests["model::iAF1260.json"].log.is_success
        assert tests["model::iAF1260.json::conditions::xyl_src"].log.is_success
        assert tests["test_code.py::test_func::iAF1260.json::xyl_src"].log.is_success
        # Test a second model
        model2 = ctx.project.load_model('e_coli_core.json')
        tests2 = model2.run_tests(display_progress=False)
        assert len(tests2) == 1
        assert tests2["model::e_coli_core.json"].log.is_success
