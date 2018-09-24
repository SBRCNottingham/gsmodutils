from gsmodutils.utils.io import load_model
from gsmodutils.utils.scrumpy import load_scrumpy_model, ParseError, get_tokens
from tutils import scrumpy_model_path, scrumpy_biomass_path, scrumpy_media_path, CleanUpDir
import tempfile
import cobra
from click.testing import CliRunner
import gsmodutils
import os
import string
import random
import pytest


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

    result = runner.invoke(gsmodutils.utils.scrumpy.scrumpy_to_cobra, [
        scrumpy_model_path,
        'MetaSal',
        '--output', output_file_path,
        '--media', scrumpy_media_path,
        '--name', 'samonella scrumpy model',
        '--objective', 'Glc_tx',
    ])


def test_load_model():
    # Test loading of scrumpy models
    model = load_scrumpy_model(scrumpy_model_path, media={"NH3_tx": -1000}, fixed_fluxes={"NOTREAL": 1000})
    assert isinstance(model, cobra.Model)


def test_cyclic_files():
    """ Shouldn't allow cyclic file definitions """

    spy_file_1 = """
Include(File2.spy)
    """
    spy_file_2 = """
Include(File1.spy)
    """
    # Write to temp dirs

    with CleanUpDir() as dir:
        filepath_1 = os.path.join(dir.path, "File1.spy")
        filepath_2 = os.path.join(dir.path, "File1.spy")
        with open(filepath_1, "w+") as file1:
            file1.write(spy_file_1)

        with open(filepath_2, "w+") as file2:
            file2.write(spy_file_2)

        with pytest.raises(ParseError):
            load_scrumpy_model(filepath_1)


def test_get_tokens():
    # Should never return empty tokens
    tokens = get_tokens("")
    assert len(tokens) == 0

    tokens = get_tokens(" ")
    assert len(tokens) == 0

    tokens = get_tokens("     ")
    assert len(tokens) == 0

    tokens = get_tokens("   A  ")
    assert len(tokens) == 1

    tokens = get_tokens("   A  BB")
    assert tuple(tokens) == ("A", "BB")
    assert len(tokens) == 2

    tokens = get_tokens("\"\'A\'\"  BB")
    assert tuple(tokens) == ("\"\'A\'\"", "BB")
    assert len(tokens) == 2

    line = "A ->B"
    tokens = get_tokens(line)
    assert len(tokens) == 3
    assert tuple(tokens) == ("A", "->", "B")

    line = "\"FOO\"<>\"BOO\""
    tokens = get_tokens(line)
    assert len(tokens) == 3
    assert tuple(tokens) == ("\"FOO\"", "<>", "\"BOO\"")

    line = "\"FOO\"<- \"POO"
    tokens = get_tokens(line)
    assert len(tokens) == 3
    assert tuple(tokens) == ("\"FOO\"", "<-", "\"POO")


