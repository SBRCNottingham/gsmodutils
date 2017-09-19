import cobra


def _get_subgraph_reactions(model, reaction_set):
    model_p = cobra.Model()
    model_p.add_reactions([model.reactions.get_by_id(rid) for rid in reaction_set])
    return model_p


def tail_metabolites(model):
    """

    :param model:
    :return:
    """
    product_metabolites = set()
    for reaction in model.reactions:
        for metabolite in reaction.products:
            product_metabolites.add(metabolite.id)

    return product_metabolites


def find_all_metabolites(model, starting_set):
    """
    Given a set of metabolites, return the subgraph that contains ones there is at least a single path towards
    :param model:
    :param starting_set:
    :return:
    """
    v = set(starting_set)
    d = set(starting_set)
    f = set()
    hp = model.copy()

    while len(v):
        i = v.pop()
        d.add(i)

        if i not in hp.metabolites:
            continue  # Skip metabolites not involved in reactions in our network

        for reaction in hp.metabolites.get_by_id(i).reactions:
            if i in reaction.reactants:
                hp.remove_metabolite_from_reaction(i, reaction.id)
                reaction.subtract_metabolites({i, reaction.metabolites[i]})

                if not len(reaction.reactants):
                    f.add(reaction.id)
                    v.update([x for x in reaction.tail if x not in d])

    return _get_subgraph_reactions(model, f)


def minimise(model, rf, target_set, starting_set):
    """

    :param model:
    :param rf:
    :param target_set:
    :param starting_set:
    :return:
    """
    f = find_all_metabolites(model, starting_set)
    modelp = model.copy()

    if not target_set.issubset(tail_metabolites(f)):
        return cobra.Model()

    for reaction in model:
        if reaction.id not in rf:

            modelp.remove_reaction(reaction.id)
            f = find_all_metabolites(modelp, starting_set)
            if not target_set.issubset(tail_metabolites(f)):
                modelp.add_reaction_obj(reaction)

    return modelp


def enumerate_pathways(model, rf, target_set, starting_set, max_depth=1000, depth=0):
    """

    :param model:
    :param rf:
    :param target_set:
    :param starting_set:
    :param max_depth:
    :param depth:
    :return:
    """
    rf = set(rf)
    f = find_all_metabolites(model, starting_set)

    f.add_reactions([model.reactions.get_by_id(rid) for rid in rf if rid in model.reactions])

    p = minimise(f, rf, target_set, starting_set)
    en = set()
    modelp = model.copy()

    if p.number_of_reactions() and depth <= max_depth:
        en.update([tuple(p.reactions.keys())])
        f = find_all_metabolites(p, starting_set)
        for r in f:
            if r.id not in rf:
                modelp.remove_reaction(r.id)
                p_s = enumerate_pathways(modelp, rf, target_set, starting_set, max_depth=max_depth, depth=depth + 1)
                if len(p_s):
                    en.update(p_s)
                rf.add(r.id)

    return en
