from __future__ import print_function
import cameo
from collections import defaultdict


def diff_models(model_a, model_b):
    '''
    Return a model design that encaptualtes the changes between two model versions
    
    This only really works if model_a is a precursor of b, otherwise you'll just get a huge number of reactions that are new/removed
    '''
    
    removed_reactions = []
    added_reactions = []
    changed_reactions = dict()
    
    
    for ra in model_a.reactions:
        
        # Reaction removed
        if ra.id not in model_b.reactions:
            removed_reactions.append(ra.id)
        else:
            # Reaction bounds aren't the same
            rb = model_b.reactions.get_by_id(ra.id)
                    
            if str(ra) != str(rb):
                changed_reactions[ra.id] = (str(ra), str(rb))
        
    added_reactions = [reaction.id for reaction in model_b.reactions if reaction.id not in model_a.reactions]
    
    
    if len(removed_reactions):
        print('REACTIONS REMOVED:')
        for r in removed_reactions:
            print("\t", r)
    
    if len(added_reactions):
        print('REACTIONS ADDED:')
        for r in added_reactions:
            print("\t", r)
            
    if len(changed_reactions):
        print('REACTIONS CHANGED:')
        for r, (ra, rb) in changed_reactions.items():
            print("\t", r, ":")
            print("\t\t", ra)
            print("\t\t", rb)
            

def _check_obj_sim(obja, objb, fields):
    '''
    Dirty function for checking if set fields are the same between two objects.
    
    This will throw excpetions if you're using it wrong but I can't tell you what they are...
    '''
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

def model_diff(model_a, model_b):
    '''
    Diff assumes l -> r (i.e. model_a is the base model)
    '''
    
    metfields = ['formula', 'charge', 'compartment', 'name']
    
    diff = dict(
        removed_metabolites=[],
        removed_reactions=[],
        reactions=[],
        metabolites=[]
    )
    
    for ma in model_a.metabolites:
        # Find removed metabolites
        try:
            mb = model_b.metabolites.get_by_id(ma.id)
        excpet KeyError:
            removed_metabolites = [mb]
            mb = None

    for mb in model_b.metabolites:
        # find added metabolites
        # find if metabolite has changed at all
        try:
            ma = model_b.metabolites.get_by_id(ma.id)
        excpet KeyError:
            ma = None
            
        if ma is not None:
            if not _check_obj_sim(ma, mb, metfields):
                pass
    
    for reaction in model_a.reactions:
        # reaction has been removed
        pass
    
    for reaction in model_b.reactions:
        # reaction is new
        # reaction has changed
            # bounds
            
            # stoichiometry
            
            # compartment
            
            # gene - reaction rule
            
            # name
            
            # subsystem
            
            # objective coef
            
            # variable kind
        pass