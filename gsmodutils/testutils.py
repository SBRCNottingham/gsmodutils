"""
Utilities for test functions

This code assumes that the namespace that python based tests are in is correctly assigned, otherwise global variables won't be present and this will throw errors

"""
from __future__ import print_function, absolute_import, division
from gsmodutils.exceptions import ProjectNamespaceError

class ModelTestSelector(object):
    
    def __init__(self, models=[], conditions=[], designs=[], *args, **kwargs):
        """
        For each parameter set run the test function with these models and save results accordingly
        
        This approach allows the reuse of test functions with multiple conditions/design parameters
        
        This 
        
        Default functionality, when using the decorator, is to perfom the test on all models and under defualt conditions.
        
        Designs and conditions will never be loaded unless specified
        
        Without this decorator, the test function would run once
        
        usage as a decorator:
        
        
        from gsmodutils.testutitls import ModelTestSelector
        @ModelTestSelector(models=['model2'], conditions=['condtion_a'], designs=['a'])
        def test_func(model, project, log):
            log.assert(True, "Works", "Does not work". "Test")
        """
        
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
                ext_model = False
                
                for cid in self.conditions:
                    
                    for did in self.designs:
                        
                        nlog = log.create_child((mn, cid, did))
                        
                        try:
                            mdl = project.load_model(mn)
                        except IOError:
                            ext_model=True
                            nlog.errors.append("model {} not found".format(mn))
                            break
                        
                        if cid is not None:
                            try:
                                project.load_conditions(cid, model=mdl)
                            except IOError:
                                nlog.errors.append("conditions {} not found".format(mn))
                                break
                            
                        if did is not None:
                            try:
                                project.load_design(did, model=mdl)
                            except IOError:
                                 nlog.errors.append("conditions {} not found".format(mn))
                                 break
                        
                        nargs=tuple([mdl, project, nlog] + list(args[3:]))
                        func(*nargs, **kwargs)
                        
                    if ext_model:
                        break
                    
        return wrapper
    
