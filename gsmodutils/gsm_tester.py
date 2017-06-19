import gsmodutils
import cameo
import sys
import StringIO
import contextlib
import os
import glob
import json
from collections import defaultdict
import time

@contextlib.contextmanager
def stdoutIO(stdout=None):
    """
    Context to capture standard output of python executed tests during run time
    This is displayed to the user for them to see
    """
    old = sys.stdout
    if stdout is None:
        stdout = StringIO.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old

class LogRecord(object):
    """Class for handling different types of errors"""
    def __init__(self, id='', parent=None):
        self.id = id
        self.parent = parent
        self.success = []
        self.error = []
        self.std_out = "" # Reserved for messages
        self.run_time = time.time()
        self.children = []
    
    def assertion(self, statement, success_msg, error_msg, desc=''):
        """
        Called within test functions to store errors and successes
        Results will be appended to the correct log reccords
        """
        if statement:
            self.success.append((success_msg, desc))
        else:
            self.error.append((error_msg, desc))
        
    def create_child(self, new_id):
        """
        Used within decorator helper functions to allow multiple tests with the same function but where other parameters change
        """
        new_id = tuple(list(self.id) + list(new_id))
        newlog = LogRecord(new_id, parent=self)
        self.children.append(newlog)
        return newlog
        
    @property
    def is_success(self):
        """
        The test function is considered a failure if there are one or more error logs
        """
        if len(self.error):
            return False
        return True
            

class TestExecSpace(object):
    """
    Object for encaptulating the namespace of user defined test modules
    
    Allows users to write functions that have access to the project modules with a small ammount of boilerplate code, ensuring that logs for errrors can be captured
    """
    
    def __init__(self, **kwargs):
        self._t_functions = []
    
    
    def add_function(self, func, *args, **kwargs):
        pass

    def run_function(self, func, args, kwargs):
        
        func(*args, **kwargs)
        

class GSMTester(object):
    """
    Loads models and executes user specified tests for the genome scale models
    """
    
    def __init__(self, project, **kwargs):
        """Creates the storage locations for logs"""
        
        if type(project) is not gsmodutils.project.GSMProject:
            raise TypeError('Requires valid gsmodutils project')
            
        self.project = project
        self.log = defaultdict(LogRecord)
        self.load_errors = []
        self.syntax_errors = dict()
        self.compile_errors = []
        self.execution_errors = []
        
        self._d_tests = dict()
        
        self._load_json_tests()
    
    def _load_json_tests(self):
        """
        populate all json files from test directory, validate format and add tests to be run
        """
        def req_fields(entry):
            _required_fields = [
                'conditions', 'models', 'designs', 'reaction_fluxes', 'required_reactions', 'description'
            ]
        
            for rf in _required_fields:
                if rf not in entry:
                    return False
            return True 
        
        load_errors = []
        invalid_tests = []
        
        for tf in glob.glob(os.path.join(self.project.tests_dir, "test_*.json")):
            id_key = os.path.basename(tf).split(".json")[0]
            with open(tf) as test_file:
                try:
                    entries = json.load(test_file)
                    
                    for entry_key, entry in entries.items():
                        if req_fields(entry):
                            self._d_tests[id_key, entry_key] = entry
                        else:
                            self.invalid_tests.append((id_key, entry_key))
                except ValueError, AttributeError:
                    # Test json is invalid format
                    self.load_errors.append((id_key, e))

    def _entry_test(self, test_id, mdl, entry):
        """
        broken up code for testing individual entries
        """
        try:
            soltuion = mdl.solve()
                
            # Test entries that require non-zero fluxes
            for rid in entry['required_reactions']:
                
                try:
                    reac = mdl.reactions.get_by_id(rid)
                    
                    if reac.flux == 0:
                        # Required reaction not active at steady state
                        msg = 'required reaction {} not active'.format(rid)
                        self.log[test_id].error.append(msg)
                    else:
                        # success log
                        msg = 'required reaction {} present at steady state'.format(rid)
                        self.log[test_id].success.append(msg)
                    
                except KeyError:
                    #TODO: log reaction not found in errors
                    err = "required reaction {} not found in model".format(rid)
                    self.log[test_id].error.append(err)
                    continue
                
            # tests for specific reaction flux ranges
            for rid, (lb, ub) in entry['reaction_fluxes'].items():
                try:
                    reac = mdl.reactions.get_by_id(rid)
                    if reac.flux < lb or reac.flux > ub:
                        err='reaction {} outside of flux bounds {}, {}'.format(rid, lb, ub)
                        self.log[test_id].error.append(err)
                    else:
                        msg='reaction {} inside flux bounds {}, {}'.format(rid, lb, ub)
                        self.log[test_id].success.append(msg)
                except KeyError:
                    # Error log of reaction not found
                    err = "required reaction {} not found in model".format(rid)
                    self.log[test_id].error.append(err)
                    continue
                
        except cameo.exceptions.Infeasible:
            # This is a full test failure (i.e. the model does not work)
            # not a conditional assertion
            self.failed_tests.append(test_id)

    def _dict_test(self, tf, entry_key, entry):
        """
        execute a standard test in the dictionary format
        """
        
        if not len(entry['conditions']):
            entry['conditions'] = [None]
            
        if not len(entry['designs']):
            entry['designs'] = [None]
        
        if not len(entry['models']):
            entry['models'] = self.project.config.models
        
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
                        self.project.load_design(design)
                    
                    test_id = ( tf, entry_key, (model_name, conditions_id, design) )
                    self._entry_test(test_id, mdl, entry)
    
    def _run_dtests(self):
        """Run entry tests"""
        for (tf, entry_key), entry in self._d_tests.items():
            self._dict_test(tf, entry_key, entry)
    
    def _exec_test(self, tf_name, compiled_code, test_func):
        """
        encapsulate a test function and run it storing the report
        """
        # Load the module in to the namespace
        with stdoutIO() as stdout:
            global_namespace = dict(
                __name__='__gsmodutils_test__',
            )
            
            try:
                exec compiled_code in global_namespace
            except Exception as ex:
                # the whole module has an error somewhere, no functions will run
                self.log[tf_name].std_out = stdout.getvalue()
                return -2, ex
            
            try:
                # Call the function
                # TODO: function args!?
                global_namespace[test_func](self.project.load_model(), self.project, self.log[tf_name])
            except Exception as ex:
                # the specific test case has an error
                self.log[tf_name].std_out = stdout.getvalue()
                return -1, ex
            
        self.log[tf_name].std_out = stdout.getvalue()
        
        return 0, None
        
    def _py_tests(self):
        """
        Loads and compiles each python test in the project's test path
        """
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
            
                
                for func in compiled_code.co_names:
                    # if the function is explicitly as test function
                    if func[:5] == "test_":
                        r_code, ex = self._exec_test(tf_name, compiled_code, func)
                        if r_code == -2:
                            # Compiled module has errors
                            self.compile_errors.append((tf_name, ex))
                            break
                        
                        elif r_code == -1:
                            # This function throws an exception on execution_errors
                            self.execution_errors.append((tf_name, func, ex))
                            continue
    
    def run_test(self, test_id):
        """Specify a single test to run"""
        pass
        
    def run_all(self):
        """
        Find and run all tests for a project
        """
        self._run_dtests()
        self._py_tests()
        
        
    def test_results(self):
        """ Return a properly formatted test results entry """
        pass
        
    
            
