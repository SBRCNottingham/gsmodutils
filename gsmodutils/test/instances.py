from abc import ABC, abstractmethod
from six import exec_
import sys
import os
import traceback
from gsmodutils.test.utils import stdout_ctx, ModelLoader


class TestInstance(ABC):

    def __init__(self, project, log, **kwargs):
        """
        Abstract base class for test instances
        """
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


class PyTestInstanceFile(TestInstance):

    def __init__(self, project, log, pyfile_path, **kwargs):
        """
        Loads a python test file and all associated python test instances
        :param pyfile_path:
        """

        super(PyTestInstanceFile).__init__(project, log, **kwargs)
        self.compiled_py = dict()
        self.syntax_errors = []
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
                self.syntax_errors.append(ex)
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
                self.children.append(PyTestInstance(func, self, self, clog))

    def run(self):
        """
        Runs all children
        :return:
        """
        for child in self.children:
            yield child.run()


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
        super(PyTestInstance).__init__(project, log, **kwargs)
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
                        tid = [mn]
                        if cid is not None and did is not None:
                            tid = (mn, cid, did)
                        elif cid is not None:
                            tid = (mn, cid)
                        elif did is not None:
                            tid = (mn, did)

                        tid = "::".join(tid)
                        model_loader = ModelLoader(self.project, mn, cid, did)
                        task_id = "{}::{}".format(_func_id, tid)
                        nlog = log.create_child(task_id, param_child=True)
                        self.children.append(PyTestInstance(self.project, nlog, func_name, self, self.pyfile,
                                                            model_loader))

    def run(self):
        if self._is_master:
            for child in self.children:
                yield child.run()
        else:
            yield self.exec()

    def exec(self, model=None):
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


class DictTestInstance(TestInstance):

    def __init__(self, project, log, **kwargs):
        super(DictTestInstance).__init__(project, log, **kwargs)

    def run(self):
        pass


class DefaultTestInstance(TestInstance):

    def __init__(self, project, log, *kwargs):
        """
        Dict test
        :param kwargs:
        """
        super(DictTestInstance).__init__(project, log, **kwargs)

    def run(self):
        pass
