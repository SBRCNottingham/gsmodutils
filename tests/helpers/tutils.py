import os
import shutil
import tempfile
from gsmodutils import GSMProject, load_model

_IAF_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'iAF1260.json')
_CORE_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'e_coli_core.json')


class CleanUpFile(object):
    """
    Context utility for ensuring that a given file is always removed after a test is run
    """
    def __init__(self, fpath):
        self._fpath = fpath

    def __enter__(self):
        pass

    def __exit__(self, *args):
        if os.path.exists(self._fpath):
            os.remove(self._fpath)


class CleanUpDir(object):
    """
    Context utility for ensuring that a given temp directory
    """
    def __init__(self, path=None):
        self.path = path

    def __enter__(self):
        if self.path is None:
            # Create a tempdir
            self.path = tempfile.mkdtemp()

        return self

    def __exit__(self, *args):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)


class FakeProjectContext(object):
    
    def __init__(self, model=None, path=None):
        """
        Assumes projectConfig class works correctly
        """
        self.path = path
        if self.path is None:
            self.path = tempfile.mkdtemp()

        self.mdl_path = tempfile.mkstemp()
        self.model = model
        if self.model is None:
            self.model = load_model(_IAF_MODEL_PATH)

    def __enter__(self):
        """
        Create a temporary gsmodutils project folder
        """
        add_models = [self.model]

        self.project = GSMProject.create_project(add_models, 'TEST PROJECT ONLY', 'test', '123@abc.com', self.path)
        return self
    
    def __exit__(self, *args):
        """
        Delete directory and model
        """
        os.remove(self.mdl_path[1])
        shutil.rmtree(self.path)
