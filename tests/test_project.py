"""
Tests for GSMProject class

TODO: tests for command line interface
"""


from __future__ import print_function, absolute_import, division
import pytest
from gsmodutils.project import GSMProject
import cameo
import os
from tutils import FakeProjectContext


def test_load_project():
    
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        assert project._project_path == ctx.path


def test_create_design():
    """
    Create a design that adds and removes reactions
    """
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        model = project.model
        
        project = GSMProject(ctx.path)
        model = project.model
        # Growth on xylose instead of glucose
        model.reactions.EX_xyl__D_e.lower_bound = -8.00
        model.reactions.EX_glc__D_e.lower_bound = 0.0 

        project.save_conditions(model, 'xylose_growth')
        
        model.reactions.ATPM.lower_bound = 8.0
        # Modified metabolite (all the water turned to hydrogen peroxide!?)
        model.metabolites.h2o_c.formula = 'H202'
        # Remove a reaction
        model.reactions.UDPGD.remove_from_model()

        # Add a reaction with a hetrologous metabolite
        metabolite = cameo.Metabolite()
        metabolite.id = 'test_c'
        metabolite.name = 'test_metabolite'
        metabolite.charge = 0
        metabolite.formula = ''
        metabolite.notes = {}
        metabolite.annotation = {}
        metabolite.compartment = 'c'
        
        model.add_metabolite(metabolite)
        
        reaction = cameo.Reaction()
    
        reaction.id = 'test_reaction'
        reaction.name = 'test'
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 1000.0
        
        model.add_reaction(reaction)
        
        reaction.add_metabolites({
            'h2o_c': -1,
            'glx_c': -1,
            'test_c': 1,
            'o2_c':1
        })
        
        model.add_demand(metabolite)
        
        # Add transporter for hetrologous metabolit
        project.save_design(model, 'test_design', 'test design 01', 'This is a test', conditions='xylose_growth')
        del model
    
        # assert design has been saved 
        assert 'test_design' in project.list_designs
        assert os.path.exists(os.path.join(ctx.path, 'designs', 'test_design.json'))
        
        # Test loading the design into the default model
        nmodel = project.load_design('test_design')
        
        nmodel.reactions.get_by_id('test_reaction')
        nmodel.metabolites.get_by_id('test_c')

        # assert that the reaction is removed 
        with pytest.raises(KeyError):
            nmodel.reactions.get_by_id('UDPGD')
        
        # assert that the metabolite is changed
        assert nmodel.metabolites.h2o_c.formula == 'H202'
        
        # assert that the reaction bounds have been modified
        assert nmodel.reactions.ATPM.lower_bound == 8.0
        
        # check conditions are loaded
        assert nmodel.reactions.EX_xyl__D_e.lower_bound == -8.00
        assert nmodel.reactions.EX_glc__D_e.lower_bound == 0.0 
        
        
def test_load_conditions():
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        model = project.model
        # Growth on xylose instead of glucose
        model.reactions.EX_xyl__D_e.lower_bound = -8.00
        model.reactions.EX_glc__D_e.lower_bound = 0.0 

        project.save_conditions(model, 'xylose_growth')
        
        # The model should be reloaded so it isn't the same reference
        del model
        new_model = project.load_conditions('xylose_growth')
        
        assert new_model.reactions.EX_xyl__D_e.lower_bound == -8.00
        assert new_model.reactions.EX_glc__D_e.lower_bound == 0.0
        
        
        
