from __future__ import absolute_import

from copy import copy, deepcopy
from cobra.core.dictlist import DictList
from six import iteritems
import cobra
import gsmodutils
from gsmodutils.utils.io import load_model
from gsmodutils.model_diff import model_diff
from gsmodutils.utils.scrumpy import load_scrumpy_model
import os
import logging
import collections
from tqdm import tqdm

logger = logging.getLogger(__name__)


class GSModutilsModel(cobra.Model):

    def __init__(self, project, mpath=None, design=None, **kwargs):
        """
        Subclass of cobra.Model this includes the project managament utils within the scope of the model
        This allows writing changes to disk and crucially - viewing a diff of things that have changed.

        :param gsmodutils.GSMProject project: must be an instance of gsmodutils.GSMproject class
        :param string mpath: project model path - must be a model included in GSMProject config models
        :param gsmodutils.StrainDesig design: gsmodutils.StrainDesign instance

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

        # Overide default_cobra behaviour
        if self.design is not None or self.mpath is not None:
            kwargs['id_or_model'] = self._load_cobra_model()

        super(GSModutilsModel, self).__init__(**kwargs)

        if self.id in [None, '']:
            self.id = self.mpath

    @property
    def model_path(self):
        """ Models path on disk """
        if self.mpath is None:
            return None

        return os.path.join(self.project.project_path, self.mpath)

    def _load_cobra_model(self):
        """
        Loads the cobra model
        :return: cobra.Model instance of self
        """
        if self.model_path is not None and not os.path.exists(self.model_path):
            raise IOError("Model file not found")

        if self.design is not None:
            return self.design.load()

        return load_model(self.model_path)

    def diff(self, model=None):
        """
        Return the difference between the in memory model and the model from disk
        See gsmodutils.model_diff.model_diff for details on the returned dict
        :return: dictionary of changed reactions, objectives, metabolites or genes
        """
        if isinstance(model, cobra.Model):
            return model_diff(model, self)

        if model is not None:
            raise TypeError("Expecting cobra.Model instance or None, got {}".format(type(model)))

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
            if self.design.is_pydesign:
                logger.error("{} is a python based design".format(self.design.id) +
                             "Trying to save a python based design in this manner will not work." +
                             "Consider saving differences as a child using GSModutilsModel.save_as_design")
                raise NotImplementedError("It is not possible to save python based designs in this manner")

            self.project.save_design(self, self.design.id, self.design.name, description=self.design.description,
                                     base_model=self.mpath, parent=self.design.parent, overwrite=True)
        else:
            with self.project.project_context_lock:
                model_type = self.mpath.split(".")[-1]

                if model_type == "json":
                    cobra.io.save_json_model(self, self.model_path, pretty=True)
                elif model_type in ["xml", "sbml"]:
                    cobra.io.write_sbml_model(self, self.model_path)
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

        Does not copy the project or design
        :return: GSModutilsModel
        """
        new = self.__class__(self.project, design=self.design, mpath=self.mpath)
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

    def load_conditions(self, conditions_id, copy=False):
        """
        Load model conditions saved in the project

        Parameters
        ----------
        conditions_id: string
            conditions identifier. Must be in project conditions file
        copy: bool
            return a copy of the model

        Returns
        -------
            GSModutilsModel
                self, or copy of self
        """
        return self.project.load_conditions(conditions_id, model=self, copy=copy)

    def to_cobra_model(self):
        """
        Returns an instance of cobra.Model without any of the useful project stuff.
        Note, uses the same solver
        :return cobra.Model
        """
        return cobra.Model(id_or_model=self)

    def add_scrumpy_reactions(self, file_or_string, overwrite=False, inplace=True):
        """
        Add Scrumpy specified reactions to the model
        :param file_or_string:
        :param overwrite:
        :return:
        """
        spy_mdl = load_scrumpy_model(file_or_string)
        return self.merge(spy_mdl, inplace=inplace)

    def collect_tests(self):
        """
        Returns test ids that apply to this model, (only bottom level tests)
        :return:
        """
        tester = self.project.project_tester()
        # Collect tests
        tester.collect_tests()
        # find all tests relating to this model
        # return the set of test ids
        apply_ids = []
        for test_id in tester.test_ids:
            test = tester.get_test(test_id)

            did = None
            if self.design is not None:
                did = self.design.id

            mid = os.path.basename(self.model_path)
            if test.applies_to_model(mid, design_id=did) and not len(test.children):
                # We only care about bottom level tests
                apply_ids.append(test_id)

        return apply_ids

    def run_tests(self, test_ids=None, display_progress=True):
        """
        Run tests for a given model
        :param test_ids:
        :param display_progress: display the progress of running tests
        :return:
        """
        tester = self.project.project_tester()
        tester.collect_tests()

        if test_ids is None:
            test_ids = self.collect_tests()
        elif not isinstance(test_ids, collections.Iterable):
            raise TypeError("test_ids must be iterable or None")

        def run_test_i(mdl, testid):
            run_mdl = mdl.copy()
            tests[testid] = tester.get_test(testid)
            tests[testid].set_override_model(run_mdl)
            tests[testid].run()

        tests = dict()
        if display_progress:
            for tid in tqdm(test_ids):
                run_test_i(self, tid)

            for tid in tests:
                print("Results for test:", tests[tid].id)
                print("\tSuccess: {}".format(tests[tid].log.is_success))

                if not tests[tid].log.is_success:
                    for error in tests[tid].log.error:
                        print(error[0])
        else:
            for tid in test_ids:
                run_test_i(self, tid)

        return tests
