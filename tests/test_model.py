from tutils import FakeProjectContext
from gsmodutils import GSMProject, GSModutilsModel
import cobra
import pytest


def test_load_model():
    """
    Most of this is for code coverage
    :return:
    """
    with FakeProjectContext() as ctx:
        ctx.add_fake_conditions()
        ctx.add_fake_designs()

        project = GSMProject(ctx.path)
        assert project.project_path == ctx.path
        model = GSModutilsModel(project)
        assert isinstance(model, cobra.Model)

        model.load_conditions("xyl_src")

        model.diff()

        model.diff(model)

        with pytest.raises(TypeError):
            model.diff("should break")

        # Test loading non design fails
        with pytest.raises(TypeError):
            GSModutilsModel(project, design={})

        with pytest.raises(TypeError):
            GSModutilsModel({})

        with pytest.raises(IOError):
            GSModutilsModel(project, mpath="/this/is/a/fake/path")

        model.save_model()
        cpy = model.to_cobra_model()
        assert not isinstance(cpy, GSModutilsModel)


def test_save_design():
    with FakeProjectContext() as ctx:
        ctx.add_fake_conditions()
        ctx.add_fake_designs()
        project = GSMProject(ctx.path)
        design = project.get_design("mevalonate_cbb")
        mdl = GSModutilsModel(project, design=design)
        mdl.save_model()

        # Can't save py designs that have been modified
        with pytest.raises(NotImplementedError):
            design = project.get_design("fake_testpy")
            mdl = GSModutilsModel(project, design=design)
            mdl.save_model()


def test_copy():
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        assert project.project_path == ctx.path
        model = GSModutilsModel(project)

        copied = model.copy()
        assert model is not copied

        for met in copied.metabolites:
            assert met is not model.metabolites.get_by_id(met.id)
            assert met.model is not model
        for gene in copied.genes:
            assert gene is not model.genes.get_by_id(gene.id)
            assert gene.model is not model


def test_load_scrumpy():
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        assert project.project_path == ctx.path
        model = GSModutilsModel(project)

        scrumpy_string = """    
External(PROTON_i, "WATER")

NADH_DH_ubi:
    "NADH" + "UBIQUINONE-8" + 4 PROTON_i -> "UBIQUINOL-8" + 3 PROTON_p + "NAD"
    ~

NADH_DH_meno:
    "NADH" + "Menaquinones" + 4 PROTON_i -> "Menaquinols" + 3 PROTON_p + "NAD"
    ~
    
Cytochrome_c_oxidase:
    1/2 "OXYGEN-MOLECULE" + "UBIQUINOL-8" + 2 PROTON_i -> "UBIQUINONE-8" + "WATER" + 2 PROTON_p
    ~


ATPSynth:
    "ADP" + "Pi" + 4 PROTON_p -> "ATP" + "WATER" + 3 PROTON_i
    ~

ATPase:
    "ATP" -> "ADP" + "Pi" + x_ATPWork
    ~
"""
        model.add_scrumpy_reactions(scrumpy_string)
        assert "NADH_DH_ubi" in model.reactions
        assert "NADH_DH_meno" in model.reactions
        assert "Cytochrome_c_oxidase" in model.reactions
        assert "ATPSynth" in model.reactions
        assert "ATPase" in model.reactions
