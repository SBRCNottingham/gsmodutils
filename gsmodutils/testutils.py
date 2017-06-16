"""
Utilities for test functions

This code assumes that the namespace that python based tests are in is correctly assigned, otherwise global variables won't be present and this will throw errors

"""
from __future__ import print_function, absolute_import, division
from gsmodutils.exceptions import ProjectNamespaceError


def _check_namespace():
    """ 
    checks that the namespace for calling tests is set correctly 
    if it isn't then the tests are being excuted outside of a gsmodutils test namespace
    If this is the case, many of the utilities provided her will not function
    """
    
    if __name__ != "__gsmodtest_env__":
        raise ProjectNamespaceError('Error, cannot call test function outside of namespace')
    

def assertion(statement, success_message, error_message):
    """Function for storing errors and successes, test assertions"""
    _check_namespace():
    if statment:
        log_report[test_id].success.append(success_message)
    else:
        log_report[test_id].error.append(error_message)
        

def model_selector(func, models=[], conditions=[], designs=[], *args, **kwargs):
    """
    For each parameter set run the test function with these models and save results accordingly
    
    This approach allows the reuse of test functions with multiple conditions/design parameters
    
    This 
    
    Default functionality, when using the decorator, is to perfom the test on all models and under defualt conditions.
    
    Designs and conditions will never be loaded unless specified
    
    Without this decorator, the test function would run once
    
    usage as a decorator:
    """
    
    _check_namespace()
    
    if not len(models):
        models = project.config.models
        
    if not len(conditions):
        conditions = [None]
    
    if not len(designs):
        designs=[None]
    
    # This nesting might not be pretty on the eyes but it gets the job done
    for model in models:
        project.load_model()
        
        for condition_id in conditions:
            if condition is not None:
                try:
                    project.load_conditions(condition_id, model=model)
                except:
                    # Store condition not found error in test log for this test
                    continue
            
            for design_id in designs:
                if design is not None:
                    try:
                        project.load_design(design_id, model=model)
                    except:
                        # Store design not found error in test log for this test
                        pass
                
                func(*args, **kwargs)

def param_rep(*args, **kwargs):
    """
    Allows varying function parameters so that a test case can be reused multiple times
    
    e.g.
    
    @param_rep(a=['1', '2', '3'])
    def func(a):
        print(a)
    
    would result in function calls
    
    func('1')
    func('2')
    func('3')
    
    """
    pass


def description(fun, description="", *args, **kwargs):
    """ Decorator to store the description for rereading log results"""
    pass
