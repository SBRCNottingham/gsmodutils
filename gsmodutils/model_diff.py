from __future__ import print_function

from cobra import Model

from gsmodutils.utils import check_obj_sim, convert_stoich, equal_stoich


def model_diff(model_a, model_b):
    """
    Returns a dictionary that contains all of the changed reactions between model a and model b
    This includes any reactions or metabolites removed, or any reactions or metabolites added/changed
    This does not say HOW a model has changed if reactions or metabolites are changed they are just included with their
    new values
    Diff assumes l -> r (i.e. model_a is the base model)
    """

    if not (isinstance(model_a, Model) and isinstance(model_b, Model)):
        raise TypeError('Can only compare cobra models')

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
            model_b.metabolites.get_by_id(ma.id)
        except KeyError:
            diff['removed_metabolites'].append(ma.id)

    for mb in model_b.metabolites:
        # find added metabolites
        # find if metabolite has changed at all
        try:
            ma = model_a.metabolites.get_by_id(mb.id)
        except KeyError:
            ma = None
            
        if ma is None or not check_obj_sim(ma, mb, metfields):
                diff['metabolites'].append(
                    dict(
                       id=mb.id,
                       notes=mb.notes,
                       compartment=mb.compartment,
                       formula=mb.formula,
                       name=mb.name,
                       charge=mb.charge,
                       annotation=mb.annotation,
                    )
                )
    
    reacfields = [
        'lower_bound', 'upper_bound', 
        'gene_reaction_rule', 'subsystem', 'name', 
        'variable_kind' 
    ]
    for ra in model_a.reactions:
        # reaction has been removed
        try:
            model_b.reactions.get_by_id(ra.id)
        except KeyError:
            diff['removed_reactions'].append(ra.id)
    
    for rb in model_b.reactions:
        # reaction is new
        try:
            ra = model_a.reactions.get_by_id(rb.id)
        except KeyError:
            ra = None
            
        # reaction has changed or is new
        if ra is None or not check_obj_sim(ra, rb, reacfields) or not equal_stoich(ra, rb):

                diff['reactions'].append(
                    dict(
                        id=rb.id,
                        lower_bound=rb.lower_bound,
                        upper_bound=rb.upper_bound,
                        gene_reaction_rule=rb.gene_reaction_rule,
                        subsystem=rb.subsystem,
                        objective_coefficient=rb.objective_coefficient,
                        name=rb.name,
                        variable_kind=rb.variable_kind,
                        metabolites=dict(convert_stoich(rb.metabolites))
                    )
                )

    # Gene reaction rules are stored in reactions, however models also contains metadata for genes
    diff['genes'] = []
    diff['removed_genes'] = []

    genefields = ["name", "annotation", "notes"]

    for ga in model_a.genes:
        try:
            model_b.genes.get_by_id(ga.id)
        except KeyError:
            diff['removed_genes'].append(ga.id)

    for gb in model_b.genes:
        try:
            ga = model_a.genes.get_by_id(gb.id)
        except KeyError:
            ga = None
            # reaction has changed or is new
        if ga is None or not check_obj_sim(ga, gb, genefields):
            diff['genes'].append(
                dict(
                    id=gb.id,
                    name=gb.name,
                    annotation=gb.annotation,
                    notes=gb.notes,
                    functional=gb.functional,
                )
            )
    return diff
