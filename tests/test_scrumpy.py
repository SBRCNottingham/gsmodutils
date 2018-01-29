from gsmodutils.utils.io import load_model
from tutils import scrumpy_model_path, scrumpy_biomass_path
import tempfile
import cobra
from click.testing import CliRunner
import gsmodutils
import os
import string
import random


def test_cli_tool():
    """ Test the command line interface parser of scrumpy files """
    output_file = ''.join(random.choice(string.ascii_uppercase + string.digits) for n in range(10)) + '.json'
    output_file_path = os.path.join(tempfile.gettempdir(), output_file)

    # Test loading of scrumpy models
    model = load_model(scrumpy_model_path)
    assert isinstance(model, cobra.Model)

    runner = CliRunner()
    result = runner.invoke(gsmodutils.utils.scrumpy.scrumpy_to_cobra, [
        scrumpy_model_path,
        'MetaSal',
        '--output', output_file_path,
        '--fixed_fluxes', scrumpy_biomass_path,
        '--name', 'samonella scrumpy model',
        '--objective', 'Glc_tx',
    ])

    assert result.exit_code == 0
    model = load_model(output_file_path)
    assert isinstance(model, cobra.Model)
    solution = model.optimize()
    assert solution.objective_value != 0.0
    os.remove(output_file_path)

    # Check the number of reactions is correct
    assert len(model.reactions) == 1229  # 1158 ??
    # Check the number of metabolites is correct
    assert len(model.metabolites) == 1130 # 1129
    # Number of transporters + metabolites should equal scrumpy's number of metabolites
    assert len(model.exchanges) == 71  # 67
