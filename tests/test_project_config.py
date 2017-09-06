"""
Tests for GSMProject class

TODO: tests for command line interface
TODO: update use the fake project (written after these tests)
"""
import os
import shutil
import tempfile

import pytest
from tutils import FakeProjectContext, CleanUpDir

from gsmodutils.exceptions import ProjectConfigurationError
from gsmodutils import GSMProject
from gsmodutils.project.project_config import ProjectConfig
from gsmodutils.project.project_config import default_model_conditionsfp, default_project_file


def project_creator(path, add_models):
    GSMProject.create_project(add_models, 'TEST PROJECT ONLY', 'test', '123@abc.com', path)


def test_create_project():
    """
    Create a test project with an example e coli model
    """
    # When writing tests use a different folder for multiprocess!

    with FakeProjectContext() as ctx:

        # Make sure all files exist
        assert os.path.exists(ctx.path)
        assert os.path.exists(os.path.join(ctx.path, default_project_file))
        assert os.path.exists(os.path.join(ctx.path, default_model_conditionsfp))

        # check project loads
        GSMProject(ctx.path)


def test_existing_project():
    """
    Force project exists exception to be thrown
    """
    with FakeProjectContext() as ctx:
        with pytest.raises(ProjectConfigurationError):
            project_creator(ctx.path, [])
    
    
def test_existing_dir():
    """
    Tests existing directory and folder
    assumes test_create_project works
    """

    with FakeProjectContext() as ctx:
        # create an existing project and delete the config files
        os.remove(os.path.join(ctx.path, default_project_file))
        os.remove(os.path.join(ctx.path, default_model_conditionsfp))

        project_creator(ctx.path, [])

        assert os.path.exists(os.path.join(ctx.path, default_project_file))
        assert os.path.exists(os.path.join(ctx.path, default_model_conditionsfp))


def test_existing_conditions_file():
    """
    Test a project where there is no project file but an existing growth conditions configuration
    """
    with FakeProjectContext() as ctx:
        os.remove(os.path.join(ctx.path, default_project_file))
        
        with pytest.raises(ProjectConfigurationError):
            project_creator(ctx.path, [])


def test_bad_model_file():
    """
    Tests a non existant model file
    """
    with CleanUpDir() as ctx:
    
        with pytest.raises(IOError):
            project_creator(ctx.path, ['/this/is/not/real.json'])
        
        assert os.path.exists(ctx.path)


def test_bad_model_file_created():
    """
    Tests a non existant model file; replicates test to make sure added directories are removed
    """
    test_path = tempfile.mkdtemp()
    shutil.rmtree(test_path)
    
    with pytest.raises(IOError):
        project_creator(test_path, ['/this/is/not/real.json'])
    
    
def test_no_model():
    # When writing tests use a different folder for multiprocess!

    with CleanUpDir() as ctx:
        project_creator(ctx.path, [])
        assert os.path.exists(ctx.path)
        assert os.path.exists(os.path.join(ctx.path, default_project_file))
        assert os.path.exists(os.path.join(ctx.path, default_model_conditionsfp))
        assert os.path.exists(os.path.join(ctx.path, 'model.json'))


def test_bad_config():
    """
    Tests that all config options should be included in a project configuration
    """
    with pytest.raises(TypeError):
        configuration = dict()
        ProjectConfig(**configuration)
