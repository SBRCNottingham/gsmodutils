"""
Tests for command line interface
"""
import pytest
from click.testing import CliRunner
import gsmodutils.cli
from gsmodutils import GSMProject, load_model
from tutils import FakeProjectContext, CleanUpFile, CleanUpDir, _CORE_MODEL_PATH
import os
import json
import cobra


def test_docker():

    with FakeProjectContext() as ctx:
        # Add some conditions and a design with a parent
        project = GSMProject(ctx.path)
        model = project.load_model()
        model.reactions.EX_xyl__D_e.lower_bound = -8.00
        model.reactions.EX_glc__D_e.lower_bound = 0.0
        project.save_conditions(model, 'xylose_growth')

        nr = model.reactions.EX_glc__D_e.copy()
        model.remove_reactions(["EX_glc__D_e"])

        project.save_design(model, 'tt1', 'tt1')
        model.add_reactions([nr])
        project.save_design(model, 'tt2', 'tt2', parent='tt1')

        runner = CliRunner()
        result = runner.invoke(gsmodutils.cli.docker, ['--project_path', ctx.path])
        assert result.exit_code == 0
        result = runner.invoke(gsmodutils.cli.docker, ['--project_path', ctx.path, '--overwrite'])
        assert result.exit_code == 0


def test_info():
    with FakeProjectContext() as ctx:
        ctx.add_fake_designs()
        ctx.add_fake_conditions()
        runner = CliRunner()
        result = runner.invoke(gsmodutils.cli.info, ['--project_path', ctx.path])
        assert result.exit_code == 0

        # Test bad project path fail
        result = runner.invoke(gsmodutils.cli.info, [])
        assert result.exit_code == -1
        # Pointless test for code coverage
        runner.invoke(gsmodutils.cli.cli)


@pytest.mark.parametrize("fmt,excode", [
    ("json", 0),
    ("yaml", 0),
    ("sbml", 0),
    ("mat", 0),
    ("spy", -1)
])
def test_export(fmt, excode):

    with FakeProjectContext() as ctx:
        runner = CliRunner()

        opt = '{}/testmdl.{}'.format(ctx.path, fmt)
        with CleanUpFile(opt):
            result = runner.invoke(gsmodutils.cli.export, [fmt, opt, '--project_path', ctx.path])
            assert result.exit_code == excode

            if excode == 0:
                # Should create the file as well as returning saying it has!
                assert os.path.exists(opt)
                # Model should load again without exceptions
                load_model(opt)

                # Should not allow overwriting/removing without flag
                result = runner.invoke(gsmodutils.cli.export, [fmt, opt, '--project_path', ctx.path])
                assert result.exit_code == -1
                assert os.path.exists(opt)

                os.remove(opt)
                # Test export of designs and conditions
                project = GSMProject(ctx.path)
                model = project.load_model()

                model.reactions.EX_xyl__D_e.lower_bound = -8.00
                model.reactions.EX_glc__D_e.lower_bound = 0.0
                project.save_conditions(model, 'xylose_growth')

                model.remove_reactions(["EX_glc__D_e"])
                project.save_design(model, 'tt1', 'tt1')

                result = runner.invoke(gsmodutils.cli.export, [fmt, opt, '--project_path', ctx.path, '--design', 'tt1'])
                assert result.exit_code == 0
                assert os.path.exists(opt)

                # test that design works correctly
                # more covered by tests for StrainDesign class, this just checks it is actually exporting a design
                l_model = load_model(opt)

                assert "EX_glc__D_e" not in l_model.reactions

                os.remove(opt)
                assert not os.path.exists(opt)

                # The same applies for exporting conditions
                result = runner.invoke(gsmodutils.cli.export, [fmt, opt, '--project_path', ctx.path, '--conditions',
                                                               'xylose_growth'])

                assert result.exit_code == 0
                assert os.path.exists(opt)

                l_model = load_model(opt)

                assert l_model.reactions.EX_xyl__D_e.lower_bound == -8.00
                assert l_model.reactions.EX_glc__D_e.lower_bound == 0.0


def test_import_conditions():
    with FakeProjectContext() as ctx:
        runner = CliRunner()

        project = GSMProject(ctx.path)
        model = project.load_model()
        model.reactions.EX_xyl__D_e.lower_bound = -8.00
        model.reactions.EX_glc__D_e.lower_bound = 0.0

        save_path = os.path.join(ctx.path, 'tp.json')

        cobra.io.save_json_model(model, save_path)

        cid = 'xylose_growth'
        result = runner.invoke(gsmodutils.cli.iconditions, [save_path, cid, '--project_path', ctx.path])
        assert result.exit_code == 0

        # Check we can actually load these conditions
        mdl = project.load_conditions(cid)

        assert mdl.reactions.EX_xyl__D_e.lower_bound == -8.0
        assert mdl.reactions.EX_glc__D_e.lower_bound == 0.0


def test_import_designs():
    with FakeProjectContext() as ctx:
        runner = CliRunner()

        name = 'test m'
        description = 'test desc'

        project = GSMProject(ctx.path)
        model = project.load_model()

        model.reactions.EX_xyl__D_e.lower_bound = -8.00
        model.remove_reactions(["EX_glc__D_e"])
        save_path = os.path.join(ctx.path, 'tp.json')
        cobra.io.save_json_model(model, save_path)

        did = 'tdes'

        opts = [
            save_path, did,
            '--project_path', ctx.path,
            '--name', name,
            '--description', description,
        ]

        result = runner.invoke(gsmodutils.cli.dimport, opts)
        assert result.exit_code == 0

        assert did in project.designs

        mdl = project.load_design(did)

        assert mdl.reactions.EX_xyl__D_e.lower_bound == -8.00
        assert "EX_glc__D_e" not in mdl.reactions

        des = project.get_design(did)
        assert des.name == name
        assert des.description == description

        # Now test inheritence
        cdid = 'tdes_child'

        rb15bp = cobra.Metabolite(id='rb15bp_c', name='D-Ribulose 1,5-bisphosphate', formula='C5H8O11P2', charge=0)
        mdl.add_metabolites(rb15bp)

        rubisco = cobra.Reaction(id="RBPC", lower_bound=0, upper_bound=1000.0, name="Ribulose-bisphosphate carboxylase")

        mdl.add_reactions([rubisco])

        stoich = {
            "3pg_c": 2.0,
            "rb15bp_c": -1.0,
            "co2_c": -1.0,
            "h2o_c": -1.0,
            "h_c": 2.0
        }

        rubisco.add_metabolites(stoich)

        cobra.io.save_json_model(mdl, save_path)

        opts = [
            save_path, cdid,
            '--project_path', ctx.path,
            '--parent', did
        ]

        name = 'test m'
        description = 'test desc'

        result = runner.invoke(gsmodutils.cli.dimport, opts, input='{}\n{}\n'.format(name, description))

        assert result.exit_code == 0

        tmdl = project.load_design(cdid)
        cdes = project.get_design(cdid)

        # Test parent loads
        assert cdes.parent.id == did
        assert tmdl.reactions.EX_xyl__D_e.lower_bound == -8.00
        assert "EX_glc__D_e" not in tmdl.reactions

        # Test child stuff
        assert "RBPC" in tmdl.reactions
        assert cdes.name == name
        assert cdes.description == description

        desc_n = "overwrite valid test"
        name_n = "overwrite"
        # Test overwrite - valid
        opts = [
            save_path, cdid,
            '--project_path', ctx.path,
            '--parent', did,
            '--description', desc_n,
            '--name', name_n,
            '--overwrite'
        ]
        result = runner.invoke(gsmodutils.cli.dimport, opts)
        assert result.exit_code == 0

        odes = project.get_design(cdid)
        assert odes.name == name_n
        assert odes.description == desc_n

        # Test non-existent parent
        opts = [
            save_path, 'should_fail',
            '--project_path', ctx.path,
            '--parent', 'notarealparentanyway'
        ]

        result = runner.invoke(gsmodutils.cli.dimport, opts)
        assert result.exit_code == -3
        assert 'should_fail' not in project.list_designs

        # Test overwrite existing fail and pass
        opts = [
            save_path, cdid,
            '--project_path', ctx.path,
            '--parent', did
        ]

        # Test overwrite existing fail and pass
        result = runner.invoke(gsmodutils.cli.dimport, opts)
        assert result.exit_code == -2


def test_addmodel():
    with FakeProjectContext() as ctx:
        runner = CliRunner()

        result = runner.invoke(gsmodutils.cli.addmodel, [_CORE_MODEL_PATH, '--project_path', ctx.path])

        assert result.exit_code == 0
        project = GSMProject(ctx.path)
        assert "e_coli_core.json" in project.config.models

        # Should fail when model already exists
        result = runner.invoke(gsmodutils.cli.addmodel, [_CORE_MODEL_PATH, '--project_path', ctx.path])
        assert result.exit_code == -1


def test_addmodel_validation():
    # Test adding a model that fails validation
    with FakeProjectContext() as ctx:
        runner = CliRunner()
        # Create a fake model which can't grow
        npath = os.path.join(ctx.path, 'tmodel.xml')
        model = load_model(_CORE_MODEL_PATH)

        for media in model.medium:
            reaction = model.reactions.get_by_id(media)
            reaction.lower_bound = 0
            reaction.upper_bound = 0

        cobra.io.write_sbml_model(model, npath)
        # Try adding it to the project, it should fail with validation on
        result = runner.invoke(gsmodutils.cli.addmodel, [npath, '--project_path', ctx.path])
        assert result.exit_code == -1
        # Pass with validation off
        result = runner.invoke(gsmodutils.cli.addmodel, [npath, '--project_path', ctx.path, '--no-validate'])
        assert result.exit_code == 0


def test_diff():
    with FakeProjectContext() as ctx:
        runner = CliRunner()

        project = GSMProject(ctx.path)
        mdl = project.load_model()

        rubisco = cobra.Reaction(id="RBPC", lower_bound=0, upper_bound=1000.0, name="Ribulose-bisphosphate carboxylase")

        mdl.add_reactions([rubisco])

        rb15bp = cobra.Metabolite(id='rb15bp_c', name='D-Ribulose 1,5-bisphosphate', formula='C5H8O11P2', charge=0)
        mdl.add_metabolites(rb15bp)

        stoich = {
            "3pg_c": 2.0,
            "rb15bp_c": -1.0,
            "co2_c": -1.0,
            "h2o_c": -1.0,
            "h_c": 2.0
        }

        rubisco.add_metabolites(stoich)

        # Remove a metabolite and reaction
        mdl.metabolites.h2o_c.remove_from_model()
        mdl.reactions.TRE6PH.remove_from_model()

        mdl.reactions.EX_glc__D_e.lower_bound = -1000

        save_path = os.path.join(ctx.path, 'tp.json')
        cobra.io.save_json_model(mdl, save_path)

        output_path = os.path.join(ctx.path, 'differ.json')
        result = runner.invoke(gsmodutils.cli.diff, [save_path, '--project_path', ctx.path, '--output', output_path,
                                                     '--names', '--base_model', 'iAF1260.json'])

        assert result.exit_code == 0
        assert os.path.exists(output_path)

        with open(output_path) as dff_file:
            diff = json.load(dff_file)

        dmdl = project.load_diff(diff)

        assert 'RBPC' in dmdl.reactions
        assert 'rb15bp_c' in dmdl.metabolites

        # add a design from a diff
        did = 'test'
        name = 'ftt'
        description = 'tt'

        opts = [
            output_path, did,
            '--project_path', ctx.path,
            '--from_diff',
            '--name', name,
            '--description', description,
        ]

        result = runner.invoke(gsmodutils.cli.dimport, opts)
        assert result.exit_code == 0
        assert did in project.list_designs

        result = runner.invoke(gsmodutils.cli.diff, [save_path, '--project_path', ctx.path, '--output', output_path,
                                                     '--names', '--base_model', 'iAF1260.json', '--parent', did])
        assert result.exit_code == 0


def test_create_project():
    runner = CliRunner()
    with CleanUpDir() as ctx:
        name = 'Test model'
        description = 'test desc'
        author = 'test author'
        email = 'test@email.com'

        inpt = '{}\n{}\n{}\n{}\n'.format(name, description, author, email)
        result = runner.invoke(gsmodutils.cli.init, [ctx.path, _CORE_MODEL_PATH], input=inpt)
        assert result.exit_code == 0

        # shouldn't raise an exception
        project = GSMProject(ctx.path)
        assert project.config.name == name
        assert project.config.description == description
        assert project.config.author == author
        assert project.config.author_email == email

        assert 'e_coli_core.json' in project.config.models

        # attempting rerun will raise exception
        result = runner.invoke(gsmodutils.cli.init, [ctx.path, _CORE_MODEL_PATH], input=inpt)
        assert result.exit_code == -1
