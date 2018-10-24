"""
Utilities for test functions

This code assumes that the namespace that python based tests are in is correctly assigned, otherwise global
variables won't be present and this will throw errors

"""
from __future__ import print_function, absolute_import, division
import time
import contextlib
import sys
from gsmodutils.utils import StringIO


class ModelTestSelector(object):
    
    def __init__(self, models=None, conditions=None, designs=None):
        """
        For each parameter set run the test function with these models and save results accordingly
        
        This approach allows the reuse of test functions with multiple conditions/design parameters
        
        This 
        
        Default functionality, when using the decorator, is to perfom the test on all models and under default
        conditions.
        
        Designs and conditions will never be loaded unless specified
        
        Without this decorator, the test function would run once
        
        usage as a decorator:

        from gsmodutils.testutitls import ModelTestSelector
        @ModelTestSelector(models=['model2'], conditions=['condtion_a'], designs=['a'])
        def test_func(model, project, log):
            log.assert(True, "Works", "Does not work". "Test")
        """

        if models is None:
            models = []

        if conditions is None:
            conditions = []

        if designs is None:
            designs = []

        self.models = models
        self.conditions = conditions
        self.designs = designs

    def __call__(self, func):
        """
        Repeatedly calls function with modfied parameters
        requires functions to have the standard form of arguments
        """
        func._is_test_selector = True
        func.models = self.models
        func.conditions = self.conditions
        func.designs = self.designs
                  
        return func


class ResultRecord(object):
    """
    Class for handling logging of errors in tester
    follows a hierarchical pattern as log records allow child records
    This is a bit of a weird data structure but the objective is to (in a future version) encapsulate all tests inside
    an instance of Test Record
    """
    def __init__(self, tid='', parent=None, param_child=False):
        self.id = tid
        self.parent = parent
        self.success = []
        self.error = []
        self.warnings = []
        self.std_out = None  # Reserved for messages
        self.run_time = time.time()
        self.children = {}
        # tells us if this is a parameter varaiation of parent (i.e. as low a level as the logs should get)
        self.param_child = param_child
        
    def assertion(self, statement, success_msg, error_msg, desc=''):
        """
        Called within test functions to store errors and successes
        Results will be appended to the correct log reccords
        """
        desc = dict(
            desc=desc,
            ex_time=time.time()
        )
        if statement:
            self.success.append((success_msg, desc))
        else:
            self.error.append((error_msg, desc))

    def warning(self, statement, message, desc=''):
        """
        Called within test functions to capture warnings about the status of models.
        If statement is true, the warning message will be stored.
        """
        if statement:
            self.warnings.append((message, desc))
    
    def add_error(self, msg, desc=''):
        """
        For errors loading tests, e.g. success cases can't be reached because the model doesn't load or can't get a
        feasable solution
        """
        desc = dict(
            desc=desc,
            ex_time=time.time()
        )
        self.error.append((msg, desc))
    
    def create_child(self, new_id, param_child=False):
        """
        Used within decorator helper functions to allow multiple tests with the same function but where other parameters
        change
        """
        if self.param_child:
            raise TypeError('Parameter variations should not have child logs')
        
        newlog = ResultRecord(new_id, parent=self, param_child=param_child)
        self.children[new_id] = newlog
        return newlog
        
    @property
    def is_success(self):
        """
        The test function is considered a failure if there are one or more error logs
        """
        if len([x for x in self.children.values() if not x.is_success]) + len(self.error):
            return False
        return True

    @property
    def log_count(self):
        """ count total errors for self and children """
        total = len(self.success) + len(self.error)
        error = len(self.error)
        
        for child in self.children.values():
            ct, ce = child.log_count
            error += ce
            total += ct
            
        return total, error

    def to_dict(self, stk=None):
        """
        converts log into dictionary form for portability
        stk stops cyclic behaviour
        """
        if stk is None:
            stk = []

        children = {}
        for child in self.children.values():
            if child.id not in stk:
                children[str(child.id)] = child.to_dict(stk=stk + [self.id])
            
        result = dict(
            id=str(self.id),
            children=children,
            error=self.error,
            success=self.success,
            is_success=self.is_success,
            run_time=self.run_time,
        )
        return result


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


class ModelLoader(object):

    def __init__(self, project, model_id, conditions_id, design_id):
        """
        Simple callback interface to load a model
        :param project: gsmodutils project
        :param model_id: model id within project
        :param conditions_id: mcondtions id within project
        :param design_id: design id within project
        """
        self.project = project
        self.model_id = model_id
        self.conditions_id = conditions_id
        self.design_id = design_id

    def load(self, log):
        mdl = self.project.load_model(self.model_id)
        if self.conditions_id is not None:
            try:
                self.project.load_conditions( self.conditions_id, model=mdl)
            except IOError as e:
                log.add_error("conditions {} not found".format(self.conditions_id), str(e))
                return None

        if self.design_id is not None:
            try:
                self.project.load_design(self.design_id, model=mdl)
            except IOError as e:
                log.add_error("design {} not found".format(self.design_id), str(e))
                return None

        return mdl
