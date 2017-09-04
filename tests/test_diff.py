import cameo
import gsmodutils.model_diff
import pytest
import cobra


def test_model_ident():
    '''
    Tests that an identical model does not produce any differences
    '''
    model_a = cameo.models.bigg.e_coli_core
    diff = gsmodutils.model_diff.model_diff(model_a, model_a.copy())
    
    assert len(diff['removed_reactions']) == 0
    assert len(diff['removed_metabolites']) == 0
    assert len(diff['reactions']) == 0
    assert len(diff['metabolites']) == 0


def test_reaction_lb_change():
    '''
    Tests that changing the lower bound on a reaction causes it to be included in the diff
    The example also checks that the change goes from L -> R
    '''
    model_a = cameo.models.bigg.e_coli_core
    model_b = cameo.models.bigg.e_coli_core
    model_b.reactions.ATPM.lower_bound = 8.0
    
    diff = gsmodutils.model_diff.model_diff(model_a, model_b)
    assert len(diff['removed_reactions']) == 0
    assert len(diff['removed_metabolites']) == 0
    assert len(diff['metabolites']) == 0
    assert len(diff['reactions']) == 1
    assert diff['reactions'][0]['id'] == model_b.reactions.ATPM.id
    assert diff['reactions'][0]['lower_bound'] == model_b.reactions.ATPM.lower_bound


def test_metabolite_formula_change():
    '''
    This tests that a small (but important) forumla change to a metabolite is picked up
    
    Note the test also makes sure that the metabolite included in the change goes from L -> R
    '''
    model_a = cameo.models.bigg.e_coli_core
    model_b = cameo.models.bigg.e_coli_core
    
    model_a.metabolites.h2o_c.formula = 'H202'
    
    diff = gsmodutils.model_diff.model_diff(model_a, model_b)
    
    assert len(diff['removed_reactions']) == 0
    assert len(diff['removed_metabolites']) == 0
    assert len(diff['reactions']) == 0
    assert len(diff['metabolites']) == 1
    assert diff['metabolites'][0]['id'] == model_a.metabolites.h2o_c.id
    assert diff['metabolites'][0]['formula'] == model_b.metabolites.h2o_c.formula


def test_gene_removal():
    model_a = cameo.models.bigg.e_coli_core
    model_b = cameo.models.bigg.e_coli_core

    cobra.manipulation.remove_genes(model_b, ['b0008'], remove_reactions=False)
    diff = gsmodutils.model_diff.model_diff(model_a, model_b)

    assert len(diff['removed_genes']) == 1

    model_a = cameo.models.bigg.e_coli_core
    model_b = cameo.models.bigg.e_coli_core

    cobra.manipulation.remove_genes(model_a, ['b0008'], remove_reactions=False)
    diff = gsmodutils.model_diff.model_diff(model_a, model_b)
    assert len(diff['genes']) == 1


def test_model_error():
    model_a = cameo.models.bigg.e_coli_core
    model_b = None

    with pytest.raises(TypeError):
       gsmodutils.model_diff.model_diff(model_a, model_b)