import os
import shutil
import tempfile

import cameo
import cobra

from gsmodutils import GSMProject
from gsmodutils.project.project_config import ProjectConfig, default_model_conditionsfp


class FakeProjectContext(object):
    
    def __init__(self):
        """
        Assumes projectConfig class works correctly
        """
        self.path = tempfile.mkdtemp()
        self.mdl_path = tempfile.mkstemp()

    def __enter__(self):
        """
        Create a temporary gsmodutils project folder
        """
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
                conditions_file=default_model_conditionsfp,
                tests_dir='tests',
                design_dir='designs'
        )
        
        self.cfg = ProjectConfig(**configuration)
        self.cfg.create_project(self.path, addmodels=add_models)

        self.project = GSMProject(self.path)
        return self
    
    def __exit__(self, *args):
        """
        Delete directory and model
        """
        os.remove(self.mdl_path[1])
        shutil.rmtree(self.path)
