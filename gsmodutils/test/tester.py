import glob
import os
from gsmodutils.test.instances import JsonTestInstance, PyTestFileInstance, DefaultTestInstance
from gsmodutils.test.utils import ResultRecord
import gsmodutils
from tqdm import tqdm


class GSMTester(object):

    def __init__(self, project):
        """
        Loads models and executes user specified tests for the genome scale models
        Creates the storage locations for logs

        Note that json test schema is validated for individual tests, not for the whole json document.
        This allows groups of tests to run with individual errors being captured.
        """
        
        if not isinstance(project, gsmodutils.GSMProject):
            raise TypeError('Requires valid gsmodutils project')
            
        self.project = project
        self.log = dict()
        self.load_errors = []
        self.invalid_tests = []
        
        self.syntax_errors = dict()

        self.python_tests = []
        self.json_tests = []
        self.default_tests = []

        self._tests_collected = False

        self._test_map = dict()
        self._id_tree = dict()
    
    def _load_json_tests(self):
        """
        populate all json files from test directory, validate format and add tests to be run
        """
        for tf in glob.glob(os.path.join(self.project.tests_dir, "test_*.json")):
            ti = JsonTestInstance(self.project, tf)
            self.log[ti.id] = ti.log
            self._test_map[ti.id] = ti
            if ti.load_errors is not None:
                self.load_errors += [ti.load_errors]
                continue

            if ti.invalid_tests is not None:
                self.invalid_tests += [ti.invalid_tests]
                continue

            self.json_tests.append(ti.id)

            for k, v in ti.get_children(flatten=True).items():
                self._test_map[k] = v

            self._id_tree[ti.id] = ti.get_id_tree()

    def _load_py_tests(self):
        """
        Loads and compiles each python test in the project's test path
        """
        test_files = os.path.join(self.project.tests_dir, "test_*.py")
        for pyfile in glob.glob(test_files):
            tf_name = os.path.basename(pyfile)
            self.log[tf_name] = ResultRecord(tf_name)
            testf = PyTestFileInstance(self.project, self.log[tf_name], pyfile)

            if testf.syntax_errors is not None:
                self.syntax_errors[pyfile] = testf.syntax_errors
                continue

            self.python_tests.append(testf.id)
            self._test_map[testf.id] = testf
            for k, v in testf.get_children(flatten=True).items():
                self._test_map[k] = v

            self._id_tree[tf_name] = testf.get_id_tree()

    def _load_default_tests(self):
        dti = DefaultTestInstance(self.project)
        self.log[dti.id] = dti.log
        self._test_map[dti.id] = dti

        self._id_tree[dti.id] = dti.get_id_tree()
        for k, v in dti.get_children(flatten=True).items():
            self._test_map[k] = v
            self.default_tests.append(v.id)

    @property
    def test_ids(self):
        return list(self._test_map.keys())

    def get_test(self, tid):
        return self._test_map[tid]

    def run_by_id(self, tid):
        """ Returns result of individual test function """

        return self._test_map[tid].run()

    def collect_tests(self):
        """
        Collects all tests but does not run them
        """
        self._load_default_tests()
        self._load_json_tests()
        self._load_py_tests()
        self._tests_collected = True

    def iter_tests(self, recollect=False):
        if not self._tests_collected or recollect:
            self.collect_tests()

        for test in self._test_map:
            yield self.run_by_id(test)

    def progress_tests(self, skip_default=False):
        """
        Run tests with a progressbar
        :param skip_default:
        :return:
        """
        for tid, test in tqdm(self._test_map.items()):
            if skip_default and tid in self.default_tests:
                continue

            if not len(test.children):
                test.run()

    def run_all(self):
        """Find and run all tests for a project, executes rather than returning generator"""
        return list(self.iter_tests())
    
    def to_dict(self):
        """ json serialisable log - call after running tests"""
        res = dict()
        for tf, log in self.log.items():
            res[tf] = log.to_dict()
        return res
