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
from itertools import chain

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
    
    def to_dict(self, stk=[]):
        """
        converts log into dictionary form for portability
        """
        children = []
        for child in self.children:
            if child.id not in stk:
                children.append(child.to_dict(stk=stk + [self.id]))
                
        result = dict(
            id=self.id,
            children=children,
            error=self.error,
            success=self.success,
            parent=self.parent.id,
            is_success=self.is_success
        )
        return result
    

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
        self.invalid_tests = []
        
        self.syntax_errors = dict()
        self.compile_errors = []
        self.execution_errors = []
        
        self._d_tests = defaultdict(dict)
        self._tests_collected = False
    
    def _load_json_tests(self):
        """
        populate all json files from test directory, validate format and add tests to be run
        """
        def req_fields(entry):
            _required_fields = [
                'conditions', 'models', 'designs', 'reaction_fluxes', 'required_reactions', 'description'
            ]
            missing_fields = [] 
            for rf in _required_fields:
                if rf not in entry:
                    
                    missing_fields.append(rf)

            return missing_fields

        for tf in glob.glob(os.path.join(self.project.tests_dir, "test_*.json")):
            id_key = os.path.basename(tf).split(".json")[0]
            with open(tf) as test_file:
                try:
                    entries = json.load(test_file)
                    
                    for entry_key, entry in entries.items():
                        missing_fields = req_fields(entry)
                        if not len(missing_fields):
                            self._d_tests[id_key][entry_key] = entry
                        else:
                            self.invalid_tests.append((id_key, entry_key, missing_fields))
                except (ValueError, AttributeError) as e:
                    # Test json is invalid format
                    self.load_errors.append((os.path.basename(tf), e))

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
                    
                    self.log[test_id].assertion(
                        reac.flux == 0,
                        success_msg='required reaction {} not active'.format(rid),
                        error_msg='required reaction {} present at steady state'.format(rid),
                        desc='.required_reaction'
                    )

                except KeyError:
                    self.log[test_id].assertion(
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
        
        return self.log[test_id]

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
                    self.log[test_id].id = test_id
                    return self._entry_test(test_id, mdl, entry)
    
    def _run_d_tests(self):
        """Run entry tests"""
        for tf in self._d_tests:
            for entry_key, entry in self._d_tests[tf].items():
                yield self._dict_test(tf, entry_key, entry)

    def _load_py_tests(self):
        """
        Loads and compiles each python test in the project's test path
        """
        self._py_tests = defaultdict(list)
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
                
                for func in compiled_code.co_names:
                    # if the function is explicitly as test function
                    if func[:5] == "test_":
                        self._py_tests[tf_name].append(func)
                        
    def _exec_test(self, tf_name, compiled_code, test_func):
        """
        encapsulate a test function and run it storing the report
        """
        # Load the module in to the namespace
        tid =  (tf_name, test_func)
        self.log[tid].id = tid
        with stdoutIO() as stdout:
            global_namespace = dict(
                __name__='__gsmodutils_test__',
            )
            
            try:
                exec compiled_code in global_namespace
            except Exception as ex:
                # the whole module has an error somewhere, no functions will run
                self.log[tid].std_out = stdout.getvalue()
                self.compile_errors.append((tf_name, ex))
                return elf.log[tid]
            
            try:
                # Call the function
                # Uses standardised prototypes
                global_namespace[test_func](self.project.load_model(), self.project, self.log[tid])
            except Exception as ex:
                # the specific test case has an error
                self.log[tid].std_out = stdout.getvalue()
                self.execution_errors.append((tf_name, test_func, ex))
                return self.log[tid]
            
        self.log[tid].std_out = stdout.getvalue()
        
        return self.log[tid]
    
    def _run_py_tests(self):
        """ Runs compiled python tests """
        for tf_name, compiled_code in self._compiled_py.items():
            for func in self._py_tests[tf_name]:
                yield self._exec_test(tf_name, compiled_code, func)
                
    @property
    def tests(self):
        return (self._d_tests, self._py_tests)
        
    def collect_tests(self):
        """
        Collects all tests but does not run them
        """
        self._load_json_tests()
        self._load_py_tests()
        self._tests_collected = True
    
    def iter_tests(self, recollect=False):
        """Go through each test and run"""
        if recollect or not self._tests_collected:
            self.collect_tests()
            
        return chain(self._run_py_tests(), self._run_d_tests())

    def run_all(self, recollect=False):
        """
        Find and run all tests for a project
        """
        return list(self.iter_tests(recollect))
    
    def test_results(self):
        """ Return a properly formatted test results entry """
        pass

        
