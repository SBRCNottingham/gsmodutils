from gsmodutils.utils.io import load_model
from tutils import scrumpy_model_path, scrumpy_biomass_path
import tempfile
import cobra
from click.testing import CliRunner
import gsmodutils
import os
import string
import random


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


def test_cli_tool():
    """ Test the command line interface parser of scrumpy files """
    # TODO: setting the objective reaction as a biomass reaction
    output_file = ''.join(random.choice(string.ascii_uppercase + string.digits) for n in range(10)) + '.json'
    output_file_path = os.path.join(tempfile.gettempdir(), output_file)
    runner = CliRunner()
    result = runner.invoke(gsmodutils.utils.scrumpy.scrumpy_to_cobra, [
        scrumpy_model_path,
        '--output', output_file_path,
        '--media', scrumpy_media_path,
    ])

    assert result.exit_code == 0
    model = load_model(output_file_path)
    assert isinstance(model, cobra.Model)
    solution = model.optimize()

    # assert solution.f > 0.0
    os.remove(output_file_path)
