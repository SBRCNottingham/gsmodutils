import cobra
import gsmodutils
from copy import copy, deepcopy
from six import iteritems
from cobra.core.dictlist import DictList
from gsmodutils.utils.io import load_model
from gsmodutils.model_diff import model_diff
import os


class GSModutilsModel(cobra.Model):

    def __init__(self, project, mpath=None, design=None, **kwargs):
        """
        Subclass of cobra.Model this includes the project managament utils within the scope of the model
        This allows writing changes to disk and crucially - viewing a diff of things that have changed.

        :param project: must be an instance of gsmodutils.GSMproject class
        :param mpath: project model path - must be a model included in GSMProject config models
        :param kwargs: standard kwargs for cobra.Model. Will ignore if 'id_or_model' param is set as this overwrites it
        """

        if design is not None and not isinstance(design, gsmodutils.StrainDesign):
            raise TypeError("Design must be none or instance of StrainDesign")

        self.design = design

        if not isinstance(project, gsmodutils.GSMProject):
            raise TypeError("Project must be a valid instance of a gsmodutils GSMProject class")

        self.project = project

        if mpath is None and self.design is None:
            mpath = project.config.default_model

        if mpath not in project.config.models and self.design is None:
            raise IOError('Model file {} not found in project, maybe you need to add it'.format(mpath))

        self.mpath = mpath

        # Overide default cobra behaviour
        if self.design is not None or self.mpath is not None:
            kwargs['id_or_model'] = self._load_cobra_model()

        super(GSModutilsModel, self).__init__(**kwargs)

        if self.id in [None, '']:
            self.id = self.mpath

    @property
    def model_path(self):
        if self.project is None:
            return None
        return os.path.join(self.project.project_path, self.mpath)

    def _load_cobra_model(self):
        """

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
            raise NotImplementedError("Saving designs in this way is not currently implemented")

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

    def save_as_design(self, design_id, name, description):
        """
        Saves the current diff status of the model as a new design
        This is just a wrapper to gsmodutils.GSMProject.save_design
        Save as a project design, if self.design is not None this is saved as a child design

        :param design_id: string identifier for design
        :param name
        :param description
        :return:
        """
        saved_design = self.project.save_design(self, design_id, name, description,
                                               base_model=self.mpath, parent=self.design)
        self.design = saved_design

    def copy(self):
        """
        Returns a deep copy of the model.
        :return: GSModutilsModel
        """
        new = self.__class__(self.project)

        do_not_copy_by_ref = {"metabolites", "reactions", "genes", "notes",
                              "annotation"}
        for attr in self.__dict__:
            if attr not in do_not_copy_by_ref:
                new.__dict__[attr] = self.__dict__[attr]
        new.notes = deepcopy(self.notes)
        new.annotation = deepcopy(self.annotation)

        new.metabolites = DictList()
        do_not_copy_by_ref = {"_reaction", "_model"}
        for metabolite in self.metabolites:
            new_met = metabolite.__class__()
            for attr, value in iteritems(metabolite.__dict__):
                if attr not in do_not_copy_by_ref:
                    new_met.__dict__[attr] = copy(
                        value) if attr == "formula" else value
            new_met._model = new
            new.metabolites.append(new_met)

        new.genes = DictList()
        for gene in self.genes:
            new_gene = gene.__class__(None)
            for attr, value in iteritems(gene.__dict__):
                if attr not in do_not_copy_by_ref:
                    new_gene.__dict__[attr] = copy(
                        value) if attr == "formula" else value
            new_gene._model = new
            new.genes.append(new_gene)

        new.reactions = DictList()
        do_not_copy_by_ref = {"_model", "_metabolites", "_genes"}
        for reaction in self.reactions:
            new_reaction = reaction.__class__()
            for attr, value in iteritems(reaction.__dict__):
                if attr not in do_not_copy_by_ref:
                    new_reaction.__dict__[attr] = copy(value)
            new_reaction._model = new
            new.reactions.append(new_reaction)
            # update awareness
            for metabolite, stoic in iteritems(reaction._metabolites):
                new_met = new.metabolites.get_by_id(metabolite.id)
                new_reaction._metabolites[new_met] = stoic
                new_met._reaction.add(new_reaction)
            for gene in reaction._genes:
                new_gene = new.genes.get_by_id(gene.id)
                new_reaction._genes.add(new_gene)
                new_gene._reaction.add(new_reaction)
        try:
            new._solver = deepcopy(self.solver)
            # Cplex has an issue with deep copies
        except Exception:  # pragma: no cover
            new._solver = copy(self.solver)  # pragma: no cover

        # it doesn't make sense to retain the context of a copied model so
        # assign a new empty context
        new._contexts = list()

        return new
