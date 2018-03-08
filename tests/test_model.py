from tutils import FakeProjectContext
from gsmodutils import GSMProject, GSModutilsModel
import cobra


def test_load_model():
    with FakeProjectContext() as ctx:
        project = GSMProject(ctx.path)
        assert project.project_path == ctx.path
        model = GSModutilsModel(project)
        assert isinstance(model, cobra.Model)


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


def test_design():
    """
    Test loading a design
    :return:
    """
    pass


def test_save():
    """
    change model, save changes
    change design, save changes
    save changes as a design
    :return:
    """
    pass