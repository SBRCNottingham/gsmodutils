import cobra


def match_reaction_by_stoich(stoichiometry, model, preserve_direction=False):
    """
    Find a reaction in a model by a stoichiometry
    :param stoichiometry:
    :param model:
    :param preserve_direction:
    :return:
    """
    stoich = dict(((x.id, value) for x, value in stoichiometry))
    rev_stoich = dict(((x.id, -value) for x, value in stoichiometry))

    for reaction in model.reactions:
        # Check if the stoichiometry is the same
        reac_stoich = dict(((x.id, value) for x, value in reaction.metabolites))

        if reac_stoich == stoich:
            return reaction, False

        if not preserve_direction:
            reac_stoich = dict(((x.id, value) for x, value in reaction.metabolites))
            if reac_stoich == rev_stoich:
                return reaction, True

    return None, False


def universal_mapper(model, metabolite_map, reaction_map, universal_model):
    """
    Given a genome scale model and a set of mappings for ids return model from a universal namespace (e.g. metanetx)

    :param model: cobra model
    :param metabolite_map:
    :param reaction_map:
    :param universal_model:
    :return:
    """
    new_model = cobra.Model()
    unmapped = dict(metabolites=set(), reactions=set())

    if not isinstance(model, cobra.Model):
        raise TypeError('Requires model to be a cobra model')

    if not isinstance(universal_model, cobra.Model):
        raise TypeError('Universal db should be an instance of a cobra model')

    for reaction in model.reactions:
        new_stoich = dict()
        # Map metabolites
        for metabolite, value in reaction.metabolites.items():
            # try from mapping
            if metabolite.id in metabolite_map:
                metab = universal_model.metabolites.get_by_id(metabolite_map[metabolite.id])
            # try loading id
            else:
                try:
                    metab = universal_model.metabolites.get_by_id(metabolite.id)
                except KeyError:
                    # not contained in the universal db
                    # use a copy from original model
                    metab = metabolite
                    unmapped['metabolites'].add(metabolite.id)

            if metab.id in new_model.metabolites:
                metab = new_model.metabolites.get_by_id(metab.id)
            else:
                # Add new metabolite to the new model
                metab = metab.copy()
                new_model.add_metabolites([metab])

            new_stoich[metab] = value

        new_reaction = cobra.Reaction()
        if reaction.id in reaction_map:
            new_reaction.id = reaction_map[reaction.id]
            # Check that the stoichiometry matches the universal db
            univ_reaction = universal_model.reactions.get_by_id(new_reaction.id)

            new_reaction.id = univ_reaction.id
            new_reaction.name = univ_reaction.name
            new_reaction.formula = univ_reaction.formula

        else:
            univ_reaction, alt_direction = match_reaction_by_stoich(new_stoich, universal_model)

            if univ_reaction is None:
                new_reaction.id = reaction.id
                unmapped['reactions'].add(new_reaction.id)
            else:
                new_reaction.rid = univ_reaction.id
                new_reaction.name = univ_reaction.name
                new_reaction.formula = univ_reaction.formula

        # Always keep bounds etc from old reaction as universal model isn't functional
        new_reaction.lower_bound = reaction.lower_bound
        new_reaction.upper_bound = reaction.upper_bound

        # Universal model will never contain genes etc
        new_reaction.gene_name_reaction_rule = reaction.gene_reaction_rule
        new_reaction.subsystem = reaction.subsystem
        new_reaction.annotation = reaction.annotation
        new_reaction.variable_kind = reaction.variable_kind

        new_model.add_reactions([new_reaction])
        new_reaction.add_metabolites(new_stoich)

    return new_model, unmapped
