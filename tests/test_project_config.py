"""
Tests for GSMProject class

TODO: tests for command line interface
TODO: update use the fake project (written after these tests)
"""
import pytest
from gsmodutils.exceptions import ProjectConfigurationError
from gsmodutils.project import GSMProject
from gsmodutils.project_config import ProjectConfig
from gsmodutils.project_config import default_model_conditionsfp, default_project_file
import cameo
import cobra
import os
import shutil
import hglib
import tempfile


def project_creator(test_path, model=True, model_path=None):
    
    add_models = []
    nmodel = None
    if model and model_path is None:
        nmodel = cameo.models.bigg.iAF1260
        mdl_path = os.path.join('/tmp', nmodel.id) 
        # save the model
        cobra.io.save_json_model(nmodel, mdl_path)
        add_models = [mdl_path]
        
    elif model_path is not None:
        add_models = [model_path]
    
    configuration = dict(description='TEST PROJECT ONLY', author='test', author_email='123@abc.com', default_model=None,
                         models=[], repository_type='hg', conditions_file=default_model_conditionsfp,
                         tests_dir='tests', design_dir='designs')
    
    cfg = ProjectConfig(**configuration)
    cfg.create_project(test_path, addmodels=add_models)
    
    return nmodel


def test_create_project():
    """
    Create a test project with an example e coli model
    """
    # When writing tests use a different folder for multiprocess!
    test_path = tempfile.mkdtemp()
    shutil.rmtree(test_path)
    project_creator(test_path)
    
    # Make sure all files exist
    assert os.path.exists(test_path)
    assert os.path.exists(os.path.join(test_path, default_project_file))
    assert os.path.exists(os.path.join(test_path, default_model_conditionsfp))
    
    # check project loads
    GSMProject(test_path)
    # check mercurial project exists and can load
    assert os.path.exists(os.path.join(test_path, '.hg'))
    hglib.open(test_path)
    
    shutil.rmtree(test_path)


def test_existing_project():
    """
    Force project exists exception to be thrown
    """
    test_path = tempfile.mkdtemp()
    
    project_creator(test_path)
    
    with pytest.raises(ProjectConfigurationError):
        project_creator(test_path)

    shutil.rmtree(test_path)
    
    
def test_existing_dir():
    """
    Tests existing directory and folder
    assumes test_create_project works
    """
    test_path = tempfile.mkdtemp()
    # create an existing project and delete the config files
    project_creator(test_path)
    
    os.remove(os.path.join(test_path, default_project_file))
    os.remove(os.path.join(test_path, default_model_conditionsfp))
    
    project_creator(test_path)
    
    assert os.path.exists(os.path.join(test_path, default_project_file))
    assert os.path.exists(os.path.join(test_path, default_model_conditionsfp))

    shutil.rmtree(test_path)
    

def test_existing_conditions_file():
    """
    Test a project where there is no project file but an existing growth conditions configuration
    """
    test_path = tempfile.mkdtemp()
    shutil.rmtree(test_path)
    
    project_creator(test_path)
    
    os.remove(os.path.join(test_path, default_project_file))
    
    with pytest.raises(ProjectConfigurationError):
        project_creator(test_path)
    
    shutil.rmtree(test_path)


def test_bad_model_file():
    """
    Tests a non existant model file
    """
    test_path = tempfile.mkdtemp()
    
    with pytest.raises(IOError):
        project_creator(test_path, model_path='/this/is/not/real.json')
    
    assert os.path.exists(test_path)
    
    shutil.rmtree(test_path)
    
    
def test_bad_model_file_created():
    """
    Tests a non existant model file; replicates test to make sure added directories are removed
    """
    test_path = tempfile.mkdtemp()
    shutil.rmtree(test_path)
    
    with pytest.raises(IOError):
        project_creator(test_path, model_path='/this/is/not/real.json')
    
    
def test_no_model():
    # When writing tests use a different folder for multiprocess!
    test_path = tempfile.mkdtemp()
    project_creator(test_path, model=False)
    assert os.path.exists(test_path)
    assert os.path.exists(os.path.join(test_path, default_project_file))
    assert os.path.exists(os.path.join(test_path, default_model_conditionsfp))
    
    assert os.path.exists(os.path.join(test_path, 'model.json'))
    
    shutil.rmtree(test_path)


def test_bad_config():
    """
    Tests that all config options should be included in a project configuration
    """
    with pytest.raises(TypeError):
        configuration = dict()
        ProjectConfig(**configuration)
    

