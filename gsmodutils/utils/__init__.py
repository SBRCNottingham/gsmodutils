import cobra
from cobra.exceptions import Infeasible
from six import string_types


class FrozenDict(dict):
    def __init__(self, iterable, **kwargs):
        super(FrozenDict, self).__init__(iterable, **kwargs)

    def popitem(self):
        raise AttributeError("'frozendict' object has no attribute 'popitem")

    def pop(self, k, d=None):
        raise AttributeError("'frozendict' object has no attribute 'pop")

    def __setitem__(self, key, value):
        raise AttributeError("'frozendict' object has no attribute '__setitem__")

    def setdefault(self, k, d=None):
        raise AttributeError("'frozendict' object has no attribute 'setdefault")

    def __delitem__(self, key):
        raise AttributeError("'frozendict' object has no attribute '__delitem__")

    def __hash__(self):
        return hash(tuple(sorted(self.items())))

    def update(self, e=None, **kwargs):
        raise AttributeError("'frozendict' object has no attribute 'update")


def check_obj_sim(obja, objb, fields):
    """
    Dirty function for checking if set fields are the same between two objects.
    
    This will throw excpetions if you're using it wrong but I can't tell you what they are...
    """
    # I felt dirty writing it and a feel dirty using it...
    for field in fields:
        attr_a = getattr(obja, field)
        attr_b = getattr(objb, field)
        
        # Minimal protections against some calls
        if type(attr_a) is not type(attr_b):
            return False
        
        # attrs are of the same type
        if attr_a != attr_b:
            return False
        
    return True


def convert_stoich(stoich):
    """
    Make a stoichiometry dict identifiers rather than metabolite objects
    """
    n_stoich = {}
    for meta, val in stoich.items():
        if type(meta) in [cobra.Metabolite]:
            n_stoich[meta.id] = val
        else:
            n_stoich[meta] = val

    return FrozenDict(n_stoich)


def equal_stoich(reaction_a, reaction_b):
    """
    Confirms if the stoich of two reactions is equivalent
    This ignores the metabolite objects in cobra reactions and converts them to metabolite ids
    """
    if not (isinstance(reaction_a, cobra.Reaction) and isinstance(reaction_b, cobra.Reaction)):
        raise TypeError('Expecing reaction object or reaction identifier string')

    return convert_stoich(reaction_a.metabolites) == convert_stoich(reaction_b.metabolites)


def biomass_debug(model, objective_reaction):
    """
    Utility for debugging a model where changes removed the ability to produce certain biomass components.
    Returns a set of components that cannot be produced
    :param model: cobrapy model instance
    :param objective_reaction: string or reaction id (must be from model)
    :return:
    """

    if not isinstance(model, cobra.Model):
        raise TypeError('Model must bt a valid cobra model object')

    if isinstance(objective_reaction, string_types):
        # Throws KeyError if not present
        objective_reaction = model.reactions.get_by_id(objective_reaction)
    elif not isinstance(objective_reaction, cobra.Reaction):
        raise TypeError('Expecing reaction object or reaction identifier string')
    elif objective_reaction.model != model:
        raise KeyError('Reaction must be from specified model')

    biomass_metabs = objective_reaction.reactants
    non_products = []
    mtest = model.copy()
    for metab in biomass_metabs:
        target = mtest.metabolites.get_by_id(metab.id)
        nobjective = mtest.add_boundary(target, type='sink', reaction_id='test_BM')
        mtest.objective = nobjective

        try:
            sol = mtest.optimize()
            if sol.objective_value == 0.0:
                non_products.append(target.id)
        # Some versions of cobra seem to throw exceptions some don't
        except Infeasible:
            non_products.append(target.id)
        nobjective.remove_from_model()

    return non_products
