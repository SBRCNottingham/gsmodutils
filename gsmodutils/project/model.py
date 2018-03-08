from __future__ import absolute_import

import cobra
import gsmodutils
from gsmodutils.utils.io import load_model
from gsmodutils.model_diff import model_diff
from gsmodutils.exceptions import ProjectNotFound
import os
import logging

logger = logging.getLogger(__name__)


class GSModutilsModel(cobra.Model):

    def __init__(self, project, mpath=None, design=None, _model=None, **kwargs):
        """
        Subclass of cobra.Model this includes the project managament utils within the scope of the model
        This allows writing changes to disk and crucially - viewing a diff of things that have changed.

        :param project: must be an instance of gsmodutils.GSMproject class
        :param mpath: project model path - must be a model included in GSMProject config models
        :param design: gsmodutils.StrainDesign instance
        :param _model: gsmodutils.GSModutilsModel - (do not use)

        :param kwargs: standard kwargs for cobra.Model. Will ignore if 'id_or_model' param is set as this overwrites it
        """
        self.design = None
        if design is not None:
            self.set_design(design)

        if not isinstance(project, gsmodutils.GSMProject):
            raise TypeError("Project must be a valid instance of a gsmodutils GSMProject class")

        self.project = project

        if mpath is None and self.design is None:
            mpath = project.config.default_model

        if mpath not in project.config.models and self.design is None:
            raise IOError('Model file {} not found in project, maybe you need to add it'.format(mpath))

        self.mpath = mpath

        # Overide default cobra behaviour
        if _model is not None and isinstance(_model, GSModutilsModel):
            kwargs['id_or_model'] = _model
        elif self.design is not None or self.mpath is not None:
            kwargs['id_or_model'] = self._load_cobra_model()

        super(GSModutilsModel, self).__init__(**kwargs)

        if self.id in [None, '']:
            self.id = self.mpath

    @property
    def model_path(self):
        if self.project is None:
            raise ProjectNotFound("Expected ")
        return os.path.join(self.project.project_path, self.mpath)

    def _load_cobra_model(self):
        """
        Loads the cobra model
        :return: cobra.Model instance of self
        """
        if not os.path.exists(self.model_path):
            raise IOError("Model file not found")

        if self.design is not None:
            return self.design.load()

        return load_model(self.model_path)

    def diff(self):
        """
        Return the difference between the in memory model and the model from disk
        See gsmodutils.model_diff.model_diff for details on the returned dict
        :return: dictionary of changed reactions, objectives, metabolites or genes
        """
        tmp_model = self._load_cobra_model()
        return model_diff(tmp_model, self)

    def set_design(self, design):
        """
        The model in question is a design
        :param design:
        :return:
        """
        if not isinstance(design, gsmodutils.StrainDesign):
            raise TypeError("Expected design to be gsmodutils StrainDesign instance")

        self.design = design

    def save_model(self):
        """
        Writes the model to the original file location.
        Uses project context lock to stop race conditions.
        :return:
        """
        if self.design is not None:
            self.save_as_design(self, self.design.id, self.design.name, self.design.description)
        else:
            with self.project.project_context_lock:
                model_type = self.mpath.split(".")[-1]

                if model_type == "json":
                    cobra.io.save_json_model(self, self.model_path, pretty=True)
                elif model_type in ["xml", "sbml"]:
                    cobra.io.save_matlab_model(self, self.model_path)
                elif model_type in ["m", "mat"]:
                    cobra.io.save_matlab_model(self, self.model_path)
                elif model_type in ["yaml", "yml"]:
                    cobra.io.save_yaml_model(self, self.model_path)

    def save_as_design(self, design_id, name, description, overwrite=False):
        """
        Saves the current diff status of the model as a new design
        This is just a wrapper to gsmodutils.GSMProject.save_design
        Save as a project design, if self.design is not None this is saved as a child design

        :param design_id: unique string identifier for design
        :param name - string a name to give to the design
        :param description string - description of design
        :param overwrite boolean - overwrite existing design of same id. Otherwise throws DesignError if present.
        :return:
        """
        saved_design = self.project.save_design(self, design_id, name, description,
                                                base_model=self.mpath, parent=self.design, overwrite=overwrite)
        self.set_design(saved_design)

    def copy(self):
        """
        Returns a deep copy of the model.
        Overides default behaviour of cobra.Model copy which makes a breaking call to self.__class__()
        :return: GSModutilsModel
        """
        new = self.__class__(project=self.project, mpath=self.mpath, design=self.design, _model=self)
        return new

    def load_conditions(self, conditions_id):
        """
        Load model conditions saved in the project
        :param conditions_id: conditions identifier. Must be in project conditions file
        :return:
        """

    def to_cobra_model(self):
        """
        Returns an instance of cobra.Model without any of the useful project stuff.
        :return:
        """
        return cobra.Model(id_or_model=self)
