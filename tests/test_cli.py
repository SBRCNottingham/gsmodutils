'''
Tests for command line interface
'''
import pytest
from click.testing import CliRunner
import gsmodutils.cli
from tutils import FakeProjectContext
import os
import tempfile


def test_docker_info():
    with FakeProjectContext() as ctx:
        runner = CliRunner()
        result = runner.invoke(gsmodutils.cli.docker, ['--project_path', ctx.path,])
        assert result.exit_code == 0
        result = runner.invoke(gsmodutils.cli.docker, ['--project_path', ctx.path, '--overwrite'])
        assert result.exit_code == 0

        result = runner.invoke(gsmodutils.cli.info, ['--project_path', ctx.path,])
        assert result.exit_code == 0

        # Test bad project path fail
        result = runner.invoke(gsmodutils.cli.info, [])
        assert result.exit_code == -1


def test_export():

    with FakeProjectContext() as ctx:
        runner = CliRunner()

        for fmt in ('json', 'yaml', 'sbml', 'm'):
            opt = tempfile.mkstemp()
            result = runner.invoke(gsmodutils.cli.export, [fmt, opt, '--project_path', ctx.path])
            assert result.exit_code == 0
            os.remove(opt)

        for fmt in ('scrumpy', 'spy'):
            opt = 'tt.{}'.format(fmt)
            result = runner.invoke(gsmodutils.cli.export, [fmt, opt, '--project_path', ctx.path])
            assert result.exit_code == -1

