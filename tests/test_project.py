"""
Tests for GSMProject class
"""


from __future__ import print_function, absolute_import, division

import os

import cobra
import pytest
from tutils import FakeProjectContext
import cameo

from gsmodutils import GSMProject
from gsmodutils.project.design import StrainDesign
from gsmodutils.exceptions import DesignError, ProjectNotFound

from cobra.exceptions import Infeasible


def test_load_project():
    
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        assert project.project_path == ctx.path


def test_create_design():
    """
    Create a design that adds and removes reactions
    """
    with FakeProjectContext() as ctx:
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
        metabolite = cobra.Metabolite()
        metabolite.id = 'test_c'
        metabolite.name = 'test_metabolite'
        metabolite.charge = 0
        metabolite.formula = ''
        metabolite.notes = {}
        metabolite.annotation = {}
        metabolite.compartment = 'c'
        
        model.add_metabolites([metabolite])
        
        reaction = cobra.Reaction()
    
        reaction.id = 'test_reaction'
        reaction.name = 'test'
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 1000.0
        
        model.add_reactions([reaction])
        
        reaction.add_metabolites({
            'h2o_c': -1,
            'glx_c': -1,
            'test_c': 1,
            'o2_c': 1
        })
        
        model.add_boundary(metabolite, type='demand')
        
        # Add transporter for hetrologous metabolite
        project.save_design(model, 'test_design', 'test design 01', 'This is a test', conditions='xylose_growth')

        # Can't save a design twice
        with pytest.raises(IOError):
            project.save_design(model, 'test_design', 'test design 01', 'This is a test', conditions='xylose_growth')

        # Invalid base model
        with pytest.raises(KeyError):
            project.save_design(model, 'test_design22', 'test design 0221', 'This is a test', base_model='NONE')

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

        project.save_conditions(model, 'xylose_growth', carbon_source="EX_xyl__D_e")
        
        # The model should be reloaded so it isn't the same reference
        del model
        new_model = project.load_conditions('xylose_growth')
        
        assert new_model.reactions.EX_xyl__D_e.lower_bound == -8.00
        assert new_model.reactions.EX_xyl__D_e.upper_bound == -8.00
        assert new_model.reactions.EX_glc__D_e.lower_bound == 0.0

        del new_model
        model = project.model
        # test using a copy of the model
        too_model = project.load_conditions('xylose_growth', model=model, copy=True)

        model.reactions.EX_xyl__D_e.lower_bound = 0.00
        assert model.reactions.EX_xyl__D_e.lower_bound != too_model.reactions.EX_xyl__D_e.lower_bound

        # Model growth when it shouldn't
        with pytest.raises(AssertionError):
            project.save_conditions(too_model, 'xylose_growth2', carbon_source="EX_xyl__D_e", observe_growth=False)

        # Bad "apply_to" model
        with pytest.raises(KeyError):
            project.save_conditions(too_model, 'xylose_growth3', carbon_source="EX_xyl__D_e", apply_to=["FOO"])

        # Bad growth target
        with pytest.raises(KeyError):
            project.save_conditions(too_model, 'xylose_growth3', carbon_source="EX_foo")


def test_project_update():
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        assert len(project.models)
        project.update()
        with pytest.raises(ProjectNotFound):
            project._project_path = 'NOT_REAL_PATH'
            project.update()

        # Test non existent designs
        with pytest.raises(DesignError):
            project.get_design("fooooo")


def test_design_parent():
    """ Design class should throw errors for cyclical parent designs, but accept valid hierarchy"""
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        # Create a design
        model = project.load_model()
        # Phosphoribulokinase reaction
        stoich = dict(
            atp_c=-1.0,
            ru5p__D_c=-1.0,
            adp_c=1.0,
            h_c=1.0,
            rb15bp_c=1.0,
        )

        rb15bp = cobra.Metabolite(id='rb15bp_c', name='D-Ribulose 1,5-bisphosphate', formula='C5H8O11P2')
        model.add_metabolites(rb15bp)

        pruk = cobra.Reaction(id="PRUK", name="Phosphoribulokinase reaction", lower_bound=-1000, upper_bound=1000)
        model.add_reactions([pruk])
        pruk.add_metabolites(stoich)

        # Rubisco reaction (Ribulose-bisphosphate carboxylase)
        stoich = {
            "3pg_c": 2.0,
            "rb15bp_c": -1.0,
            "co2_c": -1.0,
            "h2o_c": -1.0,
            "h_c": 2.0
        }

        rubisco = cobra.Reaction(id="RBPC", lower_bound=0, upper_bound=1000.0, name="Ribulose-bisphosphate carboxylase")

        model.add_reactions([rubisco])
        rubisco.add_metabolites(stoich)

        model.genes.get_by_id("b3916").knock_out()
        model.genes.get_by_id("b1723").knock_out()
        model.genes.get_by_id("b1852").knock_out()

        model.reactions.EX_glc__D_e.lower_bound = -10.0
        model.reactions.EX_nh4_e.lower_bound = -1000.0

        design = project.save_design(model, 'cbb_cycle', 'calvin cycle',
                                     description='Reactions necissary for the calvin cycle in ecoli', overwrite=True)
        # Test html string
        # Test string representation
        str(design)
        design._repr_html_()

        # Create a child of this design
        model = project.load_design('cbb_cycle')
        reaction = cobra.Reaction(id="HMGCOASi", name="Hydroxymethylglutaryl CoA synthase")

        aacoa = cobra.Metabolite(id="aacoa_c", charge=-4, formula="C25H36N7O18P3S", name="Acetoacetyl-CoA")
        hmgcoa = cobra.Metabolite(id="hmgcoa_c", charge=-5, formula="C27H40N7O20P3S", name="Hydroxymethylglutaryl CoA")

        model.add_metabolites([aacoa, hmgcoa])

        stoich = dict(
            aacoa_c=-1.0,
            accoa_c=-1.0,
            coa_c=1.0,
            h_c=1.0,
            h2o_c=-1.0,
            hmgcoa_c=1.0,
        )

        model.add_reactions([reaction])
        reaction.add_metabolites(stoich)
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 1000.0

        mev__R = cobra.Metabolite(id="mev__R_c", name="R Mevalonate", charge=-1, formula="C6H11O4")
        model.add_metabolites([mev__R])

        reaction = cobra.Reaction(id="HMGCOAR", name="Hydroxymethylglutaryl CoA reductase")
        reaction.lower_bound = -1000.0
        reaction.upper_bound = 1000.0

        stoich = dict(
            coa_c=-1.0,
            h_c=2.0,
            nadp_c=-2.0,
            nadph_c=2.0,
            hmgcoa_c=1.0,
            mev__R_c=-1.0
        )

        model.add_reactions([reaction])

        reaction.add_metabolites(stoich)

        model.add_boundary(mev__R, type='sink')  # add somewhere for mevalonate to go

        design = project.save_design(model, 'mevalonate_cbb', 'mevalonate production', parent='cbb_cycle',
                                     description='Reactions for the production of mevalonate', overwrite=True)

        des = project.get_design('mevalonate_cbb')

        inf = des.info
        pmodel = des.as_pathway_model()
        # TODO Test reactions are correct (counts should be correct)
        des.reactions_dataframe()
        des.genes_dataframe()
        des.to_dict()
        des.metabolites_dataframe()
        des.removed_genes

        # Check copying models works
        tmodel = cobra.Model()
        tmodel.id = 'test'
        des.add_to_model(tmodel, copy=True)
        # Requires a cobra model
        with pytest.raises(TypeError):
            des.add_to_model(model=None)

        # try to overwrite
        with pytest.raises(IOError):
            path = os.path.join(project._project_path, project.config.design_dir, '{}.json'.format(des.id))
            des.to_json(path, overwrite=False)

        # Try to save a design with a bad parent
        with pytest.raises(DesignError):
            des.id = 'fuuuu'
            project.save_design(model, 'mevalonate_cbbd', 'mevalonate production', parent=des,
                                description='Reactions for the production of mevalonate')


def test_save_infeasible_design():

    with FakeProjectContext() as fp:
        model = fp.project.model
        with pytest.raises(Infeasible):
            for m in model.medium:
                model.reactions.get_by_id(m).lower_bound = 0

            fp.project.save_design(model, 'foo', 'test')


def test_design_removals():

    with FakeProjectContext(model=cameo.load_model('e_coli_core')) as ctx:
        # Design with removal of reactions, metabolites, genes
        project = GSMProject(ctx.path)
        mdl = project.load_model()

        rx = mdl.reactions.get_by_id('TPI')
        rx.remove_from_model()

        gx = mdl.genes.get_by_id("b3916")
        gx.name = 'ffoods'

        mx = mdl.metabolites.get_by_id('h2o_c')
        mx.remove_from_model()

        des = project.save_design(mdl, 'test', 'test', description='test', overwrite=True)

        des._genes.append(dict(id='ffooo', name='', functional=True, notes=None, annotation={}))
        des._removed_metabolites.append('ttttesssst')
        tp = des.load()

        assert rx.id not in tp.reactions
        assert mx.id not in tp.metabolites


def test_design_class():
    """ Functionality of StrainDesign class """
    sd = StrainDesign('test', 'test', 'test', None)

    # bad parantage
    with pytest.raises(DesignError):
        sd.check_parents(p_stack=['test'])

    with pytest.raises(TypeError):
        sd.parent = "Foo"
        sd.check_parents()

    with pytest.raises(DesignError):
        sd.load()

    # bad design dict
    with pytest.raises(DesignError):
        assert not StrainDesign.validate_dict({}, throw_exceptions=False)
        StrainDesign.validate_dict({})


def test_no_model_to_add():
    with FakeProjectContext() as ctx:
        with pytest.raises(IOError):
            project = GSMProject(ctx.path)
            project.add_model('/does/not/exist')


def test_add_essential_pathways():
    """
    Test adding of json test utility
    reactions, description = '', reaction_fluxes = None,
    models = None, designs = None, conditions = None, overwrite = False
    """
    with FakeProjectContext() as fp:

        reactions = ['PYK']
        # Test bad id
        with pytest.raises(TypeError):
            fp.project.add_essential_pathway(1, reactions=reactions)

        with pytest.raises(TypeError):
            fp.project.add_essential_pathway("foo", reactions=reactions, models="String")

        # Should work without exception
        fp.project.add_essential_pathway("foo", reactions=reactions)
        # Can't add the same design twice
        with pytest.raises(IOError):
            fp.project.add_essential_pathway("foo", reactions=reactions)

        with pytest.raises(KeyError):
            fp.project.add_essential_pathway("foo2", reactions=reactions, designs=["foo"])

        with pytest.raises(KeyError):
            fp.project.add_essential_pathway("foo3", reactions=reactions, conditions=["foo"])

        with pytest.raises(KeyError):
            fp.project.add_essential_pathway("foo4", reactions=reactions, models=["foo"])
