from gsmodutils.utils.io import load_model
from tutils import scrumpy_model_path
import cobra


def test_load_model():
    """ Uses the salmonela scrumpy model (from C1Net workshop #3) """
    model = load_model(scrumpy_model_path)
    assert isinstance(model, cobra.Model)

    # Check the number of reactions is correct
    assert len(model.reactions) == 1161  # 1158 ??
    # Check the number of metabolites is correct
    assert len(model.metabolites) == 1062  # 1129
    # Number of transporters + metabolites should equal scrumpy's number of metabolites
    assert len(model.exchanges) == 69  # 67
