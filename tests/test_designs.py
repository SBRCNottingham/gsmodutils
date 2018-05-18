from gsmodutils import GSMProject
from gsmodutils.exceptions import DesignError
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

gsmdesign_uses_base_model.base_model = ""

    """

    broken_file = """
THIS IS CLEARLY BROKEN PYTHON SYNTAX
"""

    with FakeProjectContext() as ctx:
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
            design = project.get_design("t1_no_return")

        with pytest.raises(DesignError):
            design = project.get_design("t1_bad_prototype")
