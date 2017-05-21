'''
Standard cobrapy model validator

Taken from https://github.com/aebrahim/cobra_sbml_validator
(released under MIT license at the time of writing)
'''
from cobra.core.Gene import parse_gpr
from six import iteritems
from cobra.manipulation import check_mass_balance, check_reaction_bounds, check_metabolite_compartment_formula


def validate_model_file(model_path):
    '''
    Simple wrapper to load a model from a given path (handles JSON and SBML)
    '''
    import cameo
    model = cameo.load_model(model_path)
    return validate_model(model)


def validate_model(model):
    '''
    Cobra model validator 
    
    Modified from https://github.com/aebrahim/cobra_sbml_validator (MIT LICENCE)
    '''
    errors = []
    warnings = []

    # test mass balance
    for reaction in model.reactions:
        
        balance = reaction.check_mass_balance()
        
        if len(balance):
            warnings.append("reaction '%s' is not balanced for %s" %
                            (reaction.id, ", ".join(sorted(balance))))

    # try solving
    try:
        solution = model.solve()
    except Exception as e:
        errors.append("model can not be solved %s" %e.message)
        return {"errors": errors, "warnings": warnings}
    
    if solution.status != "optimal":
        errors.append("model can not be solved (status '%s')" %
                        solution.status)
        return {"errors": errors, "warnings": warnings}

    # if there is no objective, then we know why the objective was low

    if solution.objective_value <= 0:
        warnings.append("model can not produce nonzero biomass")
    if solution.objective_value <= 1e-3:
        warnings.append("biomass flux %s too low" % str(solution.objective_value))


    return {"errors": errors, "warnings": warnings, "objective": solution.objective_value}