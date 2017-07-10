import cobra
from cameo import Metabolite as cameoMetabolite


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
        if type(meta) in [cameoMetabolite, cobra.Metabolite]:
            n_stoich[meta.id] = val
        else:
            n_stoich[meta] = val
            
    return FrozenDict(n_stoich)


def equal_stoich(reaction_a, reaction_b):
    """
    Confirms if the stoich of two reactions is equivalent
    This ignores the metabolite objects in cobra reactions and converts them to metabolite ids
    """
    return convert_stoich(reaction_a.metabolites) == convert_stoich(reaction_b.metabolites)
