import cobra
from gsmodutils import GSMProject
from gsmodutils.utils.io import load_model
from gsmodutils.model_diff import model_diff
import os


class GSModutilsModel(cobra.Model):

    def __init__(self, project, mpath=None, **kwargs):
        """
        Subclass of cobra.Model this includes the project managament utils within the scope
        :param project: must be an instance of gsmodutils.GSMproject class
        :param mpath: project model path - must be a model included in GSMProject config models
        :param kwargs: standard kwargs for cobra.Model. Will ignore if 'id_or_model' param is set as this overwrites it
        """
        if not isinstance(project, GSMProject):
            raise TypeError("Project must be a valid instance of a gsmodutils GSMProject class")

        self.project = project

        if mpath is None:
            mpath = project.config.default_model

        if mpath not in project.config.models:
            raise IOError('Model file {} not found in project, maybe you need to add it'.format(mpath))

        self.mpath = mpath

        kwargs['id_or_model'] = self._load_cobra_model()
        super(GSModutilsModel, self).__init__(**kwargs)

        if self.id in [None, '']:
            self.id = self.mpath

    def _load_cobra_model(self):
        model_path = os.path.join(self.project.project_path, self.mpath)
        if not os.path.exists(model_path):
            raise IOError("Model file not found")

        return load_model(model_path)

    def diff(self):
        """
        Return the difference between the in memory model and the model from disk
        See gsmodutils.model_diff.model_diff for details on the returned dict
        :return: dictionary of changed reactions, objectives, metabolites or genes
        """
        tmp_model = self._load_cobra_model()
        return model_diff(tmp_model, self)

    def save_model(self):
        """
        Writes the model to the original file location.
        Uses project context lock to stop race conditions.
        :return:
        """
        with self.project.project_context_lock:
            pass

    def save_as_design(self, design_id):
        """
        Save as a project design
        :param design_id:
        :return:
        """
        pass

    def reload(self):
        """
        Reload from base (e.g. undo all the changes)
        :return:
        """
        pass
