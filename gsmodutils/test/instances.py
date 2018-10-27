from abc import ABCMeta, abstractmethod
from six import exec_, add_metaclass
import sys
import os
import traceback
from gsmodutils.test.utils import stdout_ctx, ModelLoader, ResultRecord
import jsonschema
from cobra.exceptions import Infeasible
import cobra
from cobra.core import get_solution
import json


@add_metaclass(ABCMeta)
class TestInstance:

    def __init__(self, project, log, **kwargs):
        """
        Abstract base class for test instances
        """
        self._override_model = None
        self.children = []
        self.log = log
        self.project = project
        self.log.__test = self

    @abstractmethod
    def run(self):
        """ Iterable (i.e should yield not return) """
        pass

    @property
    def id(self):
        return self.log.id

    def get_child_ids(self):
        ids = []
        for child in self.children:
            ids += [child.id] + child.get_child_ids()
        return ids

    def get_id_tree(self):
        tree = {}
        for child in self.children:
            tree[child.id] = child.get_id_tree()
        return tree

    def get_children(self, flatten=False):
        """
        Returns heirarchy of tests
        :bool flatten: return a flat list (id):Test_Obj instead of nested tree
        :return:
        """
        tree = {}
        if flatten:
            for child in self.children:
                tree[child.id] = child
                for k, v in child.get_children(flatten=True).items():
                    tree[k] = v
        else:
            for child in self.children:
                tree[child.id] = {
                    "tester": child,
                    "children": child.get_children()
                }
        return tree

    def set_override_model(self, model):
        """
        Sets an in memory model to be loaded on execution instead of loaded from the project
        :param model:
        :return:
        """
        self._override_model = model

    @abstractmethod
    def applies_to_model(self, model_id, design_id=None):
        pass


class PyTestFileInstance(TestInstance):

    def __init__(self, project, log, pyfile_path, **kwargs):
        """
        Loads a python test file and all associated python test instances
        :param pyfile_path:
        """

        super(PyTestFileInstance, self).__init__(project, log, **kwargs)
        self.compiled_py = dict()
        self.syntax_errors = None
        self.file_path = pyfile_path
        self.name = os.path.basename(pyfile_path)
        self.global_namespace = dict(
            __name__='__gsmodutils_test__',
        )

        with open(pyfile_path) as codestr:
            try:
                self.compiled_code = compile(codestr.read(), '', 'exec')
            except SyntaxError as ex:
                # syntax error for user written code
                # ex.lineno, ex.msg, ex.filename, ex.text, ex.offset
                self.syntax_errors = ex
                return

            with stdout_ctx() as stdout:
                try:
                    exec_(self.compiled_code, self.global_namespace)
                except Exception as ex:
                    # the whole module has an error somewhere, no functions will run
                    log.add_error("Error with code file {} error - {}".format(pyfile_path, str(ex)),
                                  ".compile_error")

            fout = stdout.getvalue()
            if fout.strip() != '':
                log.std_out += fout

            for func in filter(lambda f: f[:5] == "test_",  self.compiled_code.co_names):
                clog = log.create_child("{}::{}".format(self.name, func))
                self.children.append(PyTestInstance(self.project, clog, func, self, self))

    def run(self):
        """
        Runs all children
        :return:
        """
        for child in self.children:
            child.run()
        return self.log

    def applies_to_model(self, model_id, design_id=None):
        return False


class PyTestInstance(TestInstance):

    def __init__(self, project, log, func_name, parent, pyfile, model_loader=None, **kwargs):
        """
        Python test encapsulation object
        :param project:
        :param log:
        :param func_name:
        :param parent:
        :param pyfile:
        :param model_loader:
        :param kwargs:
        """
        super(PyTestInstance, self).__init__(project, log, **kwargs)
        self.func_name = func_name
        self.tb_info = None
        self.parent = parent
        self.pyfile = pyfile
        self._function = self.pyfile.global_namespace[func_name]
        self.model_loader = model_loader
        self._is_master = False

        if model_loader is None and hasattr(self._function, '_is_test_selector'):
            self._is_master = True
            _func_id = "{}::{}".format(self.pyfile.name, self.func_name)
            # This is not an individual test case
            if self._function.models == "*":
                self._function.models = self.project.list_models

            if self._function.designs == "*":
                self._function.designs = self.project.list_designs + [None]

            if self._function.conditions == "*":
                self._function.conditions = self.project.list_conditions + [None]

            if not len(self._function.models):
                self._function.models = [None]

            if not len(self._function.conditions):
                self._function.conditions = [None]

            if not len(self._function.designs):
                self._function.designs = [None]

            for mn in self._function.models:
                if mn is None:
                    mn = self.project.config.default_model

                for cid in self._function.conditions:

                    for did in self._function.designs:
                        # correctly setting the log id so user can easily read
                        tid = mn
                        if cid is not None and did is not None:
                            tid = (mn, cid, did)
                        elif cid is not None:
                            tid = (mn, cid)
                        elif did is not None:
                            tid = (mn, did)

                        if type(tid) is tuple:
                            tid = "::".join(tid)

                        model_loader = ModelLoader(self.project, mn, cid, did)
                        task_id = "{}::{}".format(_func_id, tid)
                        nlog = log.create_child(task_id, param_child=True)
                        self.children.append(PyTestInstance(self.project, nlog, func_name, self, self.pyfile,
                                                            model_loader))

    def run(self):
        if self._is_master:
            for child in self.children:
                child.run()
        else:
            self._fexec()
        return self.log

    def _fexec(self, model=None):
        """
        Execute the python test with encapsulation
        Passing a model allows this test to be run on any predefined cobra model, rather than one loaded from a project.
        :param model: gsmodutils model instance or none.
        :return:
        """
        with stdout_ctx() as stdout:
            if model is None and self.model_loader is None:
                model = self.project.load_model()
            elif self.model_loader is not None:
                try:
                    model = self.model_loader.load(self.log)
                except Exception as ex:
                    self.log.add_error("Error loading model {}".format(ex))
                    return self.log
            elif not isinstance(model, cobra.Model):
                raise TypeError("Expected gsmodutils or cobra model")
            try:
                # Call the function
                # Uses standardised prototypes
                self._function(model, self.project, self.log)
            except Exception as ex:
                _, _, tb = sys.exc_info()
                self.tb_info = traceback.extract_tb(tb)[-1]  # Store the traceback information
                # the specific test case has an erro
                self.log.add_error("Error executing function {} in file {} error - {}".format(self.func_name,
                                                                                              self.pyfile.file_path,
                                                                                              str(ex)),
                                   ".execution_error")

        fout = stdout.getvalue()
        if fout.strip() != '':
            self.log.std_out = fout

        return self.log

    def applies_to_model(self, model_id, design_id=None):

        if len(self.children) or design_id is None and self.model_loader.design_id is not None:
            return False
        elif self.model_loader.model_id == model_id and design_id is None:
            return True
        elif self.model_loader.model_id == model_id and design_id == self.model_loader.design_id:
            return True

        return False


class JsonTestInstance(TestInstance):

    def __init__(self, project, file_path, **kwargs):
        """
        Create sub tests from a json file
        :param project:
        :param file_path:
        :param kwargs:
        """
        id_key = os.path.basename(file_path)
        log = ResultRecord(id_key)
        super(JsonTestInstance, self).__init__(project, log, **kwargs)
        self.load_errors = None
        self.invalid_tests = None

        with open(file_path) as test_file:
            try:
                entries = json.load(test_file)
                for entry_key, entry in entries.items():
                    clog = self.log.create_child("{}::{}".format(self.id, entry_key))
                    # Test to see if individual test entries are valid or not
                    try:
                        dt = DictTestInstance(self.project, clog, entry)
                        self.children.append(dt)
                    except jsonschema.ValidationError as exp:
                        self.log.add_error(entry_key, exp)
                        self.invalid_tests = (id_key, entry_key, exp)
                        continue

            except (ValueError, AttributeError) as e:
                # Test json is invalid format
                self.load_errors = (self.id, e)

    def run(self):
        for child in self.children:
            child.run()
        return self.log

    def applies_to_model(self, model_id, design_id=None):
        return False


class DictTestInstance(TestInstance):

    schema = {
        "type": "object",
        "properties": {

            'models': {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },

            'conditions': {
                "type": "array",
                "items": {
                    "minItems": 0,
                    "type": "string"
                }
            },

            'designs': {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            'reaction_fluxes': {
                "type": "object",
                "patternProperties": {
                    "^.*$": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": {"type": "number"}
                    }
                }
            },
            'required_reactions': {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "description": {"type": "string"},
            "id": {"type": "string"}
        },
        "required": ["description", "reaction_fluxes", "conditions", "models", "designs"],
    }

    def __init__(self, project, log, entry, master=True, model_loader=None, **kwargs):
        super(DictTestInstance, self).__init__(project, log, **kwargs)

        # Test to see if individual test entries are valid or not
        # Exception should be handled when test is loaded
        jsonschema.validate(entry, DictTestInstance.schema)
        self.entry = entry.copy()
        self._master = master
        self._model_loader = model_loader

        if self._master:

            if not len(self.entry['conditions']):
                self.entry['conditions'] = [None]

            if not len(entry['designs']):
                self.entry['designs'] = [None]

            if not len(entry['models']):
                self.entry['models'] = self.project.config.models

            # Create children
            for mn in self.entry["models"]:
                for cid in self.entry["conditions"]:
                    for did in self.entry["designs"]:

                        if cid is None and did is None:
                            test_id = mn
                        elif did is None:
                            test_id = (mn, cid)
                        elif cid is None:
                            test_id = (mn, did)
                        else:
                            test_id = (mn, cid, did)

                        if type(test_id) is tuple:
                            test_id = "::".join(test_id)
                        tid = "{}::{}".format(self.id, test_id)
                        clog = self.log.create_child(tid)
                        ml = ModelLoader(self.project, mn, cid, did)
                        cinst = DictTestInstance(project, clog, entry, False, ml)
                        self.children.append(cinst)

    def run(self):
        """ Run the test (iterable) """
        if not self._master:
            self._fexec()
        else:
            for child in self.children:
                child.run()
        return self.log

    def _fexec(self, model=None):
        """
        broken up code for testing individual entries
        """
        if self._override_model is not None:
            model = self._override_model
        elif model is None and self._model_loader is None:
            model = self. project.load_model()
        elif self._model_loader is not None:
            try:
                model = self._model_loader.load(self.log)
            except Exception as ex:
                self.log.add_error("Error loading model {}".format(ex))
                return self.log

        elif not isinstance(model, cobra.Model):
            raise TypeError("Expected gsmodutils or cobra model")

        try:
            status = model.solver.optimize()

            if status == 'infeasible':
                raise Infeasible('Cannot find solution')

            # Test entries that require non-zero fluxes
            for rid in self.entry['required_reactions']:

                try:
                    reac = model.reactions.get_by_id(rid)

                    self.log.assertion(
                        reac.flux == 0,
                        success_msg='required reaction {} not active'.format(rid),
                        error_msg='required reaction {} present at steady state'.format(rid),
                        desc='.required_reaction'
                    )

                except KeyError:
                    self.log.assertion(
                        False,
                        success_msg='',
                        error_msg="required reaction {} not found in model".format(rid),
                        desc='.required_reaction .reaction_not_found'
                    )
                    continue

            # tests for specific reaction flux ranges
            for rid, (lb, ub) in self.entry['reaction_fluxes'].items():
                try:
                    reac = model.reactions.get_by_id(rid)
                    if reac.flux < lb or reac.flux > ub:
                        err = 'reaction {} outside of flux bounds {}, {}'.format(rid, lb, ub)
                        self.log.error.append((err, '.reaction_flux'))
                    else:
                        msg = 'reaction {} inside flux bounds {}, {}'.format(rid, lb, ub)
                        self.log.success.append((msg, '.reaction_flux'))
                except KeyError:
                    # Error log of reaction not found
                    self.log.assertion(
                        False,
                        success_msg='',
                        error_msg="required reaction {} not found in model".format(rid),
                        desc='.reaction_flux .reaction_not_found'
                    )
                    continue

        except Infeasible:
            # This is a full test failure (i.e. the model does not work)
            # not a conditional assertion
            self.log.add_error("No solution found with model configuration", '.no_solution')

        return self.log

    def applies_to_model(self, model_id, design_id=None):
        if len(self.children):
            return False


class DefaultTestInstance(TestInstance):

    def __init__(self, project, log_id="default_tests", **kwargs):
        """

        :param project:
        :param log_id:
        :param kwargs:
        """
        log = ResultRecord(log_id)
        super(DefaultTestInstance, self).__init__(project, log, **kwargs)

        for model_path in self.project.config.models:
            # Checking model functions without design
            tf_name = 'model::{}'.format(model_path)
            clog = self.log.create_child(tf_name)
            ti = ModelTestInstance(self.project, clog, model_path)
            self.children.append(ti)

        for ckey, cdf in self.project.conditions['growth_conditions'].items():
            # Load model that conditions applies to (default is all models in project)
            cmodels = self.project.config.models
            if 'models' in cdf and len(cdf['models']):
                cmodels = cdf['models']

            for model_path in cmodels:
                tf_name = 'model::{}::conditions::{}'.format(model_path, ckey)
                clog = self.log.create_child(tf_name)
                ti = ModelTestInstance(self.project, clog, model_path, conditions_id=ckey)
                self.children.append(ti)

        for design in self.project.list_designs:
            # Load model design with design applied
            tf_name = 'design::{}'.format(design)
            clog = self.log.create_child(tf_name)
            ti = DesignTestInstance(self.project, clog, design)
            self.children.append(ti)

    def run(self):
        for child in self.children:
            child.run()
        return self.log

    def applies_to_model(self, model_id, design_id=None):
        return False


class ModelTestInstance(TestInstance):

        def __init__(self, project, log, model_id, conditions_id=None, **kwargs):
            """

            :param project:
            :param log_id:
            :param model_id:
            :param conditions_id:
            :param kwargs:
            """
            super(ModelTestInstance, self).__init__(project, log, **kwargs)
            self.model_path = model_id
            self.conditions = conditions_id

        def run(self):
            self._fexec()
            return self.log

        def applies_to_model(self, model_id, design_id=None):

            if self.model_path == model_id and design_id is None:
                return True

            return False

        @staticmethod
        def _model_check(model):
            """
            Check a model produces a steady state flux solution
            :return: bool
            """

            status = model.solver.optimize()
            if status == 'infeasible':
                return False

            solution = get_solution(model)
            if solution.objective_value != 0:
                return True
            return False

        def load_model(self):
            try:
                model = self.project.load_model(self.model_path)
                if self.conditions is not None:
                    self.project.load_conditions(self.conditions, model=model)
            except Exception as ex:
                self.log.error.append(('Model failure loading model {}'.format(ex), '.default'))
                return None

            return model

        def _fexec(self):
            if self._override_model is None:
                model = self.load_model()
            else:
                model = self._override_model

            if model is None:
                return self.log

            growth_expected = True

            if self.conditions is not None:
                growth_expected = self.project.growth_condition(self.conditions)

            if self._model_check(model) and growth_expected:
                self.log.success.append(('Model grows', '.default'))
            elif self._model_check(model) and not growth_expected:
                self.log.error.append(('Model grows when it should not', '.default'))
            elif not self._model_check(model) and not growth_expected:
                self.log.success.append(('Model does not grow', '.default'))
            else:
                self.log.error.append(('Model does not grow', '.default'))

            return self.log


class DesignTestInstance(ModelTestInstance):

    def __init__(self, project, log, design_id, model_id=None, conditions_id=None, **kwargs):
        """

        :param project:
        :param log_id:
        :param design_id:
        :param model_id:
        :param conditions_id:
        :param kwargs:
        """
        super(DesignTestInstance, self).__init__(project, log, model_id, conditions_id, **kwargs)
        self.design = design_id

    def load_model(self):

        try:
            model = self.project.load_design(self.design)
            if self.conditions is not None:
                self.project.load_conditions(self.conditions, model=model)
        except Exception as ex:
            self.log.error.append(('Design failure loading design {}'.format(ex), '.default'))
            return None

        return model

    def _fexec(self):

        if self._override_model is None:
            model = self.load_model()
        else:
            model = self._override_model

        if model is None:
            return self.log

        if self._model_check(model):
            self.log.success.append(('Design appears to function correctly', '.default'))
        else:
            self.log.error.append(('Design fails to pass check', '.default'))
        return self.log

    def applies_to_model(self, model_id, design_id=None):
        if design_id != self.design:
            return False
        return True
