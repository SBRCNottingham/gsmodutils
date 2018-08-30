from gsmodutils import GSMProject
from gsmodutils.exceptions import DesignError, DesignOrphanError
from tutils import FakeProjectContext
import os
import pytest


def test_py_design():
    """ Tests a working py_design """

    py_design = """
def gsmdesign_tester(model, project):
    '''This is the description'''
    reaction = model.reactions.get_by_id("ATPM")
    reaction.bounds = (-999, 999)
    return model

gsmdesign_tester.name = "tester"


def gsmdesign_no_return(model, project):
    pass
    
    
def gsmdesign_bad_prototype(model):
    return model

def gsmdesign_uses_conditions(model, project):
    '''orginal description'''
    return model

gsmdesign_uses_conditions.conditions = "xylose_growth"
gsmdesign_uses_conditions.description = "overridden description"


def gsmdesign_uses_base_model(model, project):
    return model

gsmdesign_uses_base_model.base_model = "e_coli_core.json"


def gsmdesign_bad_base_model(model, project):
    return model

gsmdesign_bad_base_model.base_model = "e_coli_core"

    """

    broken_file = """
THIS IS CLEARLY BROKEN PYTHON SYNTAX
"""

    with FakeProjectContext(use_second_model=True) as ctx:
        project = GSMProject(ctx.path)

        ndpath = os.path.join(project.design_path, 'design_t1.py')
        # Write the design
        with open(ndpath, 'w+') as desf:
            desf.write(py_design)

        # The file is broken but but the project should still load
        ndpath = os.path.join(project.design_path, 'design_broken.py')
        with open(ndpath, 'w+') as desb:
            desb.write(broken_file)

        # Should load without error
        design = project.get_design("t1_tester")
        assert design.is_pydesign
        assert design.name == "tester"
        assert design.parent is None
        assert design.description == "This is the description"

        mdl = design.load()
        # Check that the code has executed
        reaction = mdl.reactions.get_by_id("ATPM")
        assert reaction.lower_bound == -999
        assert reaction.upper_bound == 999

        model = project.model
        # Growth on xylose instead of glucose
        model.reactions.EX_xyl__D_e.lower_bound = -8.00
        model.reactions.EX_glc__D_e.lower_bound = 0.0

        project.save_conditions(model, 'xylose_growth', carbon_source="EX_xyl__D_e")

        design = project.get_design("t1_uses_conditions")

        assert design.description == "overridden description"
        assert design.conditions == "xylose_growth"
        mdl = design.load()

        assert mdl.reactions.EX_glc__D_e.lower_bound == 0
        assert mdl.reactions.EX_xyl__D_e.lower_bound == -8.00

        with pytest.raises(DesignError):
            project.get_design("t1_no_return")

        with pytest.raises(DesignError):
            project.get_design("t1_bad_prototype")

        design = project.get_design("t1_uses_base_model")
        assert design.base_model == "e_coli_core.json"
        assert len(design.load().reactions) == 95   # Make sure the base model is loaded

        with pytest.raises(DesignError):
            project.get_design("t1_bad_base_model")


def test_parantage():
    """ Tests for child and parent designs. Take a breath, this is some pretty confusing logic. """

    py_design = """
def gsmdesign_thanos(model, project):
    reaction = model.reactions.get_by_id("ATPM")
    reaction.bounds = (-999, 999)
    return model

gsmdesign_thanos.parent = "mevalonate_cbb"

def gsmdesign_child_of_thanos(model, project):
    reaction = model.reactions.get_by_id("ATPM")
    reaction.lower_bound  = 0
    return model     

gsmdesign_child_of_thanos.parent = "t1_thanos"


def gsmdesign_invalid_parent_id(model, project):
    reaction = model.reactions.get_by_id("ATPM")
    reaction.lower_bound  = 0
    return model

gsmdesign_invalid_parent_id.parent = "thanos"

"""
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        # Create existing json designs
        ctx.add_fake_designs()

        ndpath = os.path.join(project.design_path, 'design_t1.py')
        # Write the design
        with open(ndpath, 'w+') as desf:
            desf.write(py_design)

        d1 = project.get_design("t1_thanos")
        assert d1.id == "t1_thanos"
        assert d1.parent.id == "mevalonate_cbb"
        m1 = d1.load()
        assert m1.reactions.get_by_id("RBPC").lower_bound == 0

        design = project.get_design("t1_child_of_thanos")
        assert design.parent.id == "t1_thanos"
        assert design.parent.parent.id == "mevalonate_cbb"

        mdl = design.load()  # t1_child_of_thanos
        reaction = mdl.reactions.get_by_id("ATPM")
        assert reaction.lower_bound == 0

        mdl2 = design.parent.load()  # should be t1_thanos
        assert mdl2.design.id == "t1_thanos"
        assert mdl2.design.parent.id == "mevalonate_cbb"
        reaction = mdl2.reactions.get_by_id("ATPM")
        assert reaction.lower_bound == -999

        mdl2.reactions.EX_xyl__D_e.lower_bound = -8.00
        mdl2.save_as_design("json_child_of_thanos", "jsonchild", "json_child_of_thanos")

        design2 = project.get_design("json_child_of_thanos")
        assert design2.parent.id == "t1_thanos"
        assert design2.id == design2.load().design.id
        assert design2.parent.parent.parent.id == "cbb_cycle"

        mdl3 = design2.load()
        reaction = mdl3.reactions.get_by_id("ATPM")
        assert reaction.lower_bound == -999
        assert mdl3.reactions.EX_xyl__D_e.lower_bound == -8.00

        # shows that the very top level json design is still working
        assert mdl3.reactions.get_by_id("RBPC").lower_bound == 0

        # This design shouldn't load as the parent id ref is wrong
        with pytest.raises(DesignError):
            project.get_design("t1_invalid_parent_id")
