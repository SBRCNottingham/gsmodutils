import contextlib
import glob
import json
import os
import sys
from collections import defaultdict
from io import StringIO

from cobra.core import get_solution
from cobra.exceptions import Infeasible
from six import exec_

import gsmodutils
from gsmodutils.test.utils import TestRecord


@contextlib.contextmanager
def stdout_ctx(stdout=None):
    """
    Context to capture standard output of python executed tests during run time
    This is displayed to the user for them to see after the tests are run
    """
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old
    

class GSMTester(object):
    """
    Loads models and executes user specified tests for the genome scale models
    """
    def __init__(self, project):
        """Creates the storage locations for logs"""
        
        if not isinstance(project, gsmodutils.GSMProject):
            raise TypeError('Requires valid gsmodutils project')
            
        self.project = project
        self.log = defaultdict(TestRecord)
        self.load_errors = []
        self.invalid_tests = []
        
        self.syntax_errors = dict()
        
        self._task_execs = dict()
        self._child_tests = defaultdict(list)  # store for top level tests
        
        self.python_tests = defaultdict(list)
        self.json_tests = defaultdict(dict)
        self.default_tests = dict()

        self._tests_collected = False
        
        self.sub_tests = defaultdict(list)

        self._task_id_map = dict()  # Map an id to task to execute
    
    def _load_json_tests(self):
        """
        populate all json files from test directory, validate format and add tests to be run
        """
        def req_fields(entryi):
            _required_fields = [
                'conditions', 'models', 'designs', 'reaction_fluxes', 'required_reactions', 'description'
            ]
            missing_fieldsi = []
            for rf in _required_fields:
                if rf not in entryi:
                    
                    missing_fieldsi.append(rf)

            return missing_fieldsi

        for tf in glob.glob(os.path.join(self.project.tests_dir, "test_*.json")):
            id_key = os.path.basename(tf)
            with open(tf) as test_file:
                try:
                    entries = json.load(test_file)
                
                    self.log[id_key].id = id_key
                    for entry_key, entry in entries.items():
                        missing_fields = req_fields(entry)
                        t_args = (id_key, entry_key)
                        self._child_tests[id_key].append(t_args)
                        if not len(missing_fields):
                            self.json_tests[id_key][entry_key] = entry
                            self.log[id_key].create_child(entry_key)
                            self._task_execs[t_args] = self._dict_test
                            self._task_id_map[id_key] = t_args
                        else:
                            self.log[id_key].add_error(entry_key, missing_fields)
                            self.invalid_tests.append((id_key, entry_key, missing_fields))
                    
                except (ValueError, AttributeError) as e:
                    # Test json is invalid format
                    self.load_errors.append((id_key, e))
                
                self._task_execs[tf] = self.iter_basetf
                self._task_id_map[tf] = tf

    @staticmethod
    def _entry_test(log, mdl, entry):
        """
        broken up code for testing individual entries
        """
        try:
            status = mdl.solver.optimize()

            if status == 'infeasible':
                raise Infeasible('Cannot find solution')

            # Test entries that require non-zero fluxes
            for rid in entry['required_reactions']:
                
                try:
                    reac = mdl.reactions.get_by_id(rid)
                    
                    log.assertion(
                        reac.flux == 0,
                        success_msg='required reaction {} not active'.format(rid),
                        error_msg='required reaction {} present at steady state'.format(rid),
                        desc='.required_reaction'
                    )

                except KeyError:
                    log.assertion(
                        False,
                        success_msg='',
                        error_msg="required reaction {} not found in model".format(rid),
                        desc='.required_reaction .reaction_not_found'
                    )
                    continue
                
            # tests for specific reaction flux ranges
            for rid, (lb, ub) in entry['reaction_fluxes'].items():
                try:
                    reac = mdl.reactions.get_by_id(rid)
                    if reac.flux < lb or reac.flux > ub:
                        err = 'reaction {} outside of flux bounds {}, {}'.format(rid, lb, ub)
                        log.error.append((err, '.reaction_flux'))
                    else:
                        msg = 'reaction {} inside flux bounds {}, {}'.format(rid, lb, ub)
                        log.success.append((msg, '.reaction_flux'))
                except KeyError:
                    # Error log of reaction not found
                    log.assertion(
                        False,
                        success_msg='',
                        error_msg="required reaction {} not found in model".format(rid),
                        desc='.reaction_flux .reaction_not_found'
                    )
                    continue
                
        except Infeasible:
            # This is a full test failure (i.e. the model does not work)
            # not a conditional assertion
            log.add_error("No solution found with model configuration", '.no_solution')
        
        return log

    def _dict_test(self, id_key, entry_key):
        """
        execute a standard test in the dictionary format
        """
        entry = self.json_tests[id_key][entry_key]
        
        if not len(entry['conditions']):
            entry['conditions'] = [None]
            
        if not len(entry['designs']):
            entry['designs'] = [None]
        
        if not len(entry['models']):
            entry['models'] = self.project.config.models
        
        top_log = self.log[id_key].children[entry_key]
        # load models
        for model_name in entry['models']:
            # load conditions
            mdl = self.project.load_model(model_name)
            for conditions_id in entry['conditions']:
                # load condtions
                if conditions_id is not None:
                    mdl = self.project.load_conditions(model=mdl, conditions_id=conditions_id)
                
                for design in entry['designs']:
                    if design is not None:
                        self.project.load_design(design, model=mdl)
                    
                    if design is None and conditions_id is None:
                        test_id = model_name
                    elif design is None:
                        test_id = (model_name, conditions_id)
                    elif conditions_id is None:
                        test_id = (model_name, design)
                    else:
                        test_id = (model_name, conditions_id, design)
                    
                    log = top_log.create_child(test_id)
                    
                    return self._entry_test(log, mdl, entry)

    def _load_py_tests(self):
        """
        Loads and compiles each python test in the project's test path
        """

        self._compiled_py = dict()
        test_files = os.path.join(self.project.tests_dir, "test_*.py")
        for pyfile in glob.glob(test_files):
            tf_name = os.path.basename(pyfile)
            with open(pyfile) as codestr:
                try:
                    compiled_code = compile(codestr.read(), '', 'exec')
                except SyntaxError as ex:
                    # syntax error for user written code
                    # ex.lineno, ex.msg, ex.filename, ex.text, ex.offset
                    self.syntax_errors[pyfile] = ex
                    continue

                self._compiled_py[tf_name] = compiled_code
                self.log[tf_name].id = tf_name
                
                for func in compiled_code.co_names:
                    # if the function is explicitly as test function
                    if func[:5] == "test_":
                        self.log[tf_name].create_child(func)
                        self.python_tests[tf_name].append(func)
                        
                        args = (tf_name, func)
                        task_id = "{}_{}".format(tf_name, func)
                        self._task_execs[args] = self._exec_test
                        self._task_id_map[task_id] = args
                        self._child_tests[tf_name].append(args)

            self._task_execs[tf_name] = self.iter_basetf
            self._task_id_map[tf_name] = tf_name

    def _exec_test(self, tf_name, test_func):
        """
        encapsulate a test function and run it storing the report
        """
        compiled_code = self._compiled_py[tf_name] 
        log = self.log[tf_name].children[test_func]
        # Load the module in to the namespace
        # Capture the standard out rather than dumping it to terminal
        with stdout_ctx() as stdout:
            global_namespace = dict(
                __name__='__gsmodutils_test__',
            )
            
            try:
                exec_(compiled_code, global_namespace)
            except Exception as ex:
                # the whole module has an error somewhere, no functions will run
                log.add_error("Error with code file {} error - {}".format(tf_name, str(ex)), ".compile_error")

            try:
                # Call the function
                # Uses standardised prototypes
                global_namespace[test_func](self.project.load_model(), self.project, log)
            except Exception as ex:
                # the specific test case has an erro
                log.add_error("Error executing function {} in file {} error - {}".format(test_func, tf_name, str(ex)),
                              ".execution_error")
        
        fout = stdout.getvalue()
        if fout.strip() != '':
            log.std_out = fout
        
        return log
    
    def _run_py_tests(self):
        """ Runs compiled python tests """
        for tf_name, compiled_code in self._compiled_py.items():
            for func in self.python_tests[tf_name]:
                yield self._exec_test(tf_name, func)

    @staticmethod
    def _model_check(model):
        """
        Check a model produces a steady state flux solution
        :return: bool
        """

        status = model.solver.optimize()
        if status == 'infeasible':
            return False

        solution = get_solution(model)
        if solution.objective_value != 0:
            return True
        return False

    def _df_model_test(self, log, model_path, conditions=None):
        model = self.project.load_model(model_path)

        if conditions is not None:
            growth_expected = self.project.growth_condition(conditions)
            self.project.load_conditions(conditions, model=model)
        else:
            growth_expected = True

        if self._model_check(model) and growth_expected:
            log.success.append(('Model grows', '.default'))
        elif self._model_check(model) and not growth_expected:
            log.error.append(('Model grows when it should not', '.default'))
        elif not self._model_check(model) and not growth_expected:
            log.success.append(('Model does not grow', '.default'))
        else:
            log.error.append(('Model does not grow', '.default'))

        return log

    def _df_design_test(self, log, design):
        model = self.project.load_design(design)
        if self._model_check(model):
            log.success.append(('Design functions', '.default'))
        else:
            log.error.append(('Design failure', '.default'))
        return log

    def _load_default_tests(self):
        """Tests that users don't need to write - load models, load designs, load conditions"""
        df_log = self.log['default_tests']

        for model_path in self.project.config.models:
            # Checking model functions without design
            tf_name = 'model_{}'.format(model_path)
            log = df_log.create_child(tf_name)
            kwargs = dict(log=log, model_path=model_path)
            self.default_tests[tf_name] = (self._df_model_test, kwargs)
            self._task_execs[tf_name] = self._exec_default
            self._task_id_map[tf_name] = tf_name

        for ckey, cdf in self.project.conditions['growth_conditions'].items():
            # Load model that conditions applies to (default is all models in project)
            cmodels = self.project.config.models
            if 'models' in cdf and len(cdf['models']):
                cmodels = cdf['models']

            for model_path in cmodels:
                tf_name = 'conditions_{}:model_{}'.format(model_path, ckey)
                log = df_log.create_child(tf_name)
                kwargs = dict(log=log, model_path=model_path, conditions=ckey)
                self.default_tests[tf_name] = (self._df_model_test, kwargs)
                self._task_execs[tf_name] = self._exec_default
                self._task_id_map[tf_name] = tf_name

        for design in self.project.list_designs:
            # Load model design with design applied
            tf_name = 'design_{}'.format(design)
            log = df_log.create_child(tf_name)
            kwargs = dict(log=log, design=design)
            self.default_tests[tf_name] = (self._df_design_test, kwargs)
            self._task_execs[tf_name] = self._exec_default
            self._task_id_map[tf_name] = tf_name

    def _exec_default(self, tid):
        return self.default_tests[tid][0](**self.default_tests[tid][1])

    @property
    def test_ids(self):
        return list(self._task_id_map.keys())

    def run_by_id(self, tid):
        """ Returns result of individual test function """
        targs = self._task_id_map[tid]
        func = self._task_execs[targs]
        
        if func == self.iter_basetf:
            return list(func(targs))[0]
        
        return func(*targs)

    def collect_tests(self):
        """
        Collects all tests but does not run them
        """
        self._load_default_tests()
        self._load_json_tests()
        self._load_py_tests()
        self._tests_collected = True

    def iter_basetf(self, base_file):
        """ Given a base test file (.json or .py) """
        yield self.log[base_file]  # first element is always the top level log
        for args in self._child_tests[base_file]:
            yield self._task_execs[args](*args)
    
    def iter_tests(self, recollect=False, skip_default=False):
        """Generate each test function"""
        if recollect or not self._tests_collected:
            self.collect_tests()
        
        for tid, func in self._task_execs.items():
            # skip base files - this just runs all the tests twice
            if func == self._exec_default and not skip_default:
                yield func(tid)
            elif func != self.iter_basetf:
                yield func(*tid)  # generator for the test

    def run_all(self, recollect=False):
        """Find and run all tests for a project, executes rather than returning generator"""
        return list(self.iter_tests(recollect))
    
    def to_dict(self):
        """ json serialisable log - call after running tests"""
        res = dict()
        for tf, log in self.log.items():
            res[tf] = log.to_dict()
        return res
