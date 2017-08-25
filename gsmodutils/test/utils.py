"""
Utilities for test functions

This code assumes that the namespace that python based tests are in is correctly assigned, otherwise global
variables won't be present and this will throw errors

"""
from __future__ import print_function, absolute_import, division
import time


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
        if not len(self.models):
            self.models = [None]
        
        self.conditions = conditions
        if not len(self.conditions):
            self.conditions = [None]
        
        self.designs = designs
        if not len(designs):
            self.designs = [None]

    def __call__(self, func):
        """
        Repeatedly calls function with modfied parameters
        requires functions to have the standard form of arguments
        """
        def wrapper(*args, **kwargs):
            project = args[1]
            log = args[2]
            
            for mn in self.models:
                if mn is None:
                    mn = project.config.default_model
                ext_model = False
                
                for cid in self.conditions:
                    
                    for did in self.designs:
                        # correctly setting the log id so user can easily read
                        tid = mn
                        if cid is not None and did is not None:
                            tid = (mn, cid, did)
                        elif cid is not None:
                            tid = (mn, cid)
                        elif did is not None:
                            tid = (mn, did)
                        
                        nlog = log.create_child(tid, param_child=True)
                        
                        try:
                            mdl = project.load_model(mn)
                        except IOError as e:
                            ext_model = True
                            nlog.add_error("model {} not found".format(mn), str(e))
                            break
                        
                        if cid is not None:
                            try:
                                project.load_conditions(cid, model=mdl)
                            except IOError as e:
                                nlog.add_error("conditions {} not found".format(mn), str(e))
                                break
                            
                        if did is not None:
                            try:
                                project.load_design(did, model=mdl)
                            except IOError as e:
                                nlog.add_error("design {} not found".format(mn), str(e))
                                break
                        
                        nargs = tuple([mdl, project, nlog] + list(args[3:]))
                        func(*nargs, **kwargs)

                    if ext_model:
                        break
                  
        return wrapper


class TestRecord(object):
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
        
        newlog = TestRecord(new_id, parent=self, param_child=param_child)
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
                children[child.id] = child.to_dict(stk=stk + [self.id])
            
        result = dict(
            id=self.id,
            children=children,
            error=self.error,
            success=self.success,
            is_success=self.is_success,
            run_time=self.run_time,
        )
        return result
