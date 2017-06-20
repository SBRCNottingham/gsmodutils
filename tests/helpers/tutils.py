import cameo
import cobra
import tempfile
from gsmodutils.project import GSMProject
from gsmodutils.project_config import ProjectConfig
from gsmodutils.project_config import _default_model_conditionsfp, _default_project_file
import os
import shutil

class FakeProjectContext(object):
    
    def __init__(self):
        '''
        Assumes projectConfig class works correctly
        '''
        self.path = tempfile.mkdtemp()
        self.mdl_path = tempfile.mkstemp()


    def __enter__(self):
        '''
        Create a temporary gsmodutils project folder
        '''
        self.model = cameo.models.bigg.iAF1260
        cobra.io.save_json_model(self.model, self.mdl_path[1])
        add_models = [self.mdl_path[1]]
        configuration = dict(
                description='TEST PROJECT ONLY',
                author='test',
                author_email='123@abc.com',
                default_model=None,
                models=[],
                repository_type='hg',
                conditions_file=_default_model_conditionsfp,
                tests_dir='tests',
                design_dir='designs'
        )
        
        self.cfg = ProjectConfig(**configuration)
        self.cfg.create_project(self.path, addmodels=add_models)
        return self
    
    def __exit__(self, *args):
        '''
        Delete directory and model
        '''
        shutil.rmtree(self.path)
        os.remove(self.mdl_path[1])
    
    def create_test(self):
        pass
    
    def create_design(self):
        pass
