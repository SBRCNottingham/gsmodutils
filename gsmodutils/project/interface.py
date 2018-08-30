from __future__ import print_function, absolute_import, division

import glob
import json
import os
import fasteners

from cobra.exceptions import Infeasible
from six import string_types

from gsmodutils.exceptions import ProjectNotFound, DesignError, DesignNotFoundError, ValidationError
from gsmodutils.model_diff import model_diff
from gsmodutils.project.design import StrainDesign
from gsmodutils.project.model import GSModutilsModel
from gsmodutils.project.project_config import ProjectConfig, default_project_file
from gsmodutils.test.tester import GSMTester
from gsmodutils.utils import validator
from gsmodutils.utils.io import load_medium
import logging
import jsonschema


logger = logging.getLogger(__name__)


class GSMProject(object):

    conditions_schema = {
        "type": "object",
        "properties": {
            "growth_conditions": {
                "type": "object",
                "patternProperties": {
                    "^.*$": {
                        "type": "object",
                        "properties": {
                            "observe_growth": {"type": "bool"},
                            "models": {
                                "type": "array",
                                "items": {"type": "string"}
                            },

                            "carbon_source": {"type": "string"},
                            "media": {
                                "type": "object",
                                "patternProperties": {
                                    "^.*$": {
                                        "type": "number",
                                    }
                                },
                            }
                        }
                    }
                }
            },
            "carbon_sources": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }

        }
    }

    def __init__(self, path="."):
        """
        Project class finds a gsmodutlils.json file in a given path and creates a project which allows a user to load:
            Models included within the project
            Designs that the model uses
        """
        logger.info("Attempting to load project in path {}".format(path))
        self._project_path = os.path.abspath(path)
        self.update()
        self._conditions_file = os.path.join(self._project_path, self.config.conditions_file)
        self._designs_store = dict()  # In memory store for designs
        self._py_compiled_designs = dict()
        self._py_func_mapper = dict()

    @property
    def project_path(self):
        return self._project_path

    @property
    def _context_file(self):
        return os.path.join(self._project_path, default_project_file)

    def _load_config(self, configuration):
        """
        Sanatizes configuration input
        """
        jsonschema.validate(configuration, ProjectConfig.config_schema)
        self.config = ProjectConfig(**configuration)

    @property
    def tests_dir(self):
        """ Tests directory """
        return os.path.join(self._project_path, self.config.tests_dir)

    def project_tester(self):
        """Creates a tester for this project instance"""
        return GSMTester(self)

    def run_tests(self):
        """
        Returns the log output of all the tests
        :return:
        """
        tester = GSMTester(self)
        tester.collect_tests()
        tester.progress_tests()
        return tester.to_dict()

    @property
    def project_context_lock(self):
        """
        Returns a gloab project lock to stop multiple operations on files.
        This software is not designed to be used in multiple user environments, so this is slow. However, it provides
        some degree of protection for the user against modifying the same files
        """
        lock_path = os.path.join(self._project_path, '.gsmodultils_project_lock')
        return fasteners.InterProcessLock(lock_path)

    def update(self):
        """
        Updates this class from configuration file
        """
        if not os.path.exists(self._project_path):
            logger.error("Failed to find project path {}".format(self._project_path))
            raise ProjectNotFound('Project path {} does not exist'.format(self._project_path))
        
        if not os.path.exists(self._context_file):
            logger.error("Failed to find project config file {}".format(self._context_file))
            raise ProjectNotFound(
                'Project settings file {} in {} does not exist'.format(default_project_file, self._project_path))
        
        with open(self._context_file) as ctxfile:
            self._load_config(json.load(ctxfile))

        self._conditions_file = os.path.join(self._project_path, self.config.conditions_file)

    def get_conditions(self, update=False):
        """
        Load the saved conditions file
        """
        if update:
            self.update()
            
        with open(self._conditions_file) as cf:
            cdf = json.load(cf)
        return cdf
    
    @property
    def conditions(self):
        """
        Different model conditions
        :return: dict of model conditions
        """
        return self.get_conditions()

    def iter_models(self):
        """
        Generator for models
        """
        for mdl_path in self.config.models:
            yield self.load_model(mpath=mdl_path)

    @property
    def list_models(self):
        return self.config.models

    @property
    def models(self):
        """
        Lists all the models that can be loaded
        """
        return list(self.iter_models())

    def load_model(self, mpath=None):
        """
        Get a model stored by the project
        mpath refers to the relative path of the model
        """
        if mpath is None:
            mpath = self.config.default_model
        
        if mpath not in self.config.models:
            raise IOError('Model file {} not found in project, maybe you need to add it'.format(mpath))

        mdl = GSModutilsModel(self, mpath)
        mdl._gsm_model_path = mpath
        return mdl

    @property
    def model(self):
        """
        Returns default model for project
        """
        return self.load_model()

    def add_model(self, model_path, validate=True):
        """
        Add a model given a path to it copy it to model directory unless its in the project path already.
        """
        if not os.path.exists(model_path):
            raise IOError('No such model {}'.format(model_path))

        model_path = os.path.abspath(model_path)

        if validate:
            result = validator.validate_model_file(model_path)
            if len(result["errors"]):
                raise ValidationError("Model contains errors, will not add to project")

        # check model isn't in the project already
        npath = os.path.basename(model_path)
        if npath in self.config.models:
            raise KeyError('Model of the same name already included in project')

        # add model to project and save configuration
        self.config.models.append(npath)
        self.config.save_config(self.project_path)

    @property
    def design_path(self):
        return os.path.join(self._project_path, self.config.design_dir)

    @property
    def _py_designs(self):
        """
        Compile python designs and list them
        :return: list of python designs
        """
        py_designs = []
        designs_direct = glob.glob(os.path.join(self.design_path, 'design_*.py'))

        # Read the python file for design functions
        for pyfile in designs_direct:
            mtime = os.path.getmtime(pyfile)
            # Only recompile if its been modified
            if pyfile not in self._py_compiled_designs or self._py_compiled_designs[pyfile][0] != mtime:
                dnames, compiled_code = StrainDesign.compile_pydesign(pyfile)
                self._py_compiled_designs[pyfile] = (mtime, dnames, compiled_code)

                for dn, func in dnames.items():
                    self._py_func_mapper[dn] = (func, pyfile)

            py_designs += list(self._py_compiled_designs[pyfile][1].keys())

        return py_designs

    @property
    def _json_designs(self):
        designs_direct = glob.glob(os.path.join(self.design_path, '*.json'))
        return [os.path.basename(dpath).split(".json")[0] for dpath in designs_direct]

    @property
    def list_designs(self):
        """ List designs stored in design dir """
        json_designs = self._json_designs
        py_designs = self._py_designs

        return json_designs + py_designs

    @property
    def designs(self):
        """
        Return list of all the designs stored for the project
        """
        for design in self.list_designs:
            try:
                self.get_design(design)
            except DesignError:
                pass

        return self._designs_store

    def _load_py_design(self, dname):
        """ Load a python design """
        # Map to correct pyfile
        func_name, pyfile = self._py_func_mapper[dname]
        return StrainDesign.from_pydesign(self, dname, func_name, self._py_compiled_designs[pyfile][2])

    def get_design(self, design):
        """
        Get the StrainDesign object (not resulting model) of a design
        :param design: design identifier
        :return:
        """
        if design not in self.list_designs:
            raise DesignNotFoundError("Design of name {} not found in project".format(design))

        if design in self._json_designs:
            des_path = os.path.join(self._project_path, self.config.design_dir, '{}.json'.format(design))
            self._designs_store[design] = StrainDesign.from_json(design, des_path, self)
        else:
            try:
                self._designs_store[design] = self._load_py_design(design)
            except Exception as exp:
                raise DesignError(str(exp))

        return self._designs_store[design]

    def load_design(self, design, model=None, copy=False):
        """
        Returns a model with a specified design modification
        
        Design must either be a design stored in the folder path or a path to a json file
        The json file should conform to the same standard as a json model
        
        required fields:
            "metabolites":[]
            "reactions":[]
            "description": "", 
            "notes": {}, 
            "genes": [], 
            "id":""
        
        optional fields:
            "parent": str - parent design to be applied first
            "conditions": ""
            "removed_reactions":[]
            "removed_metabolites":[]
        
        Note if conditions is specified it is loaded first
        other bounds are set afterwards
        """
        des = self.get_design(design)
        if model is not None:
            return des.add_to_model(model, copy=copy)

        return des.load()

    def save_design(self, model, did, name, description='', conditions=None, base_model=None, parent=None,
                    overwrite=False):
        """
        Creates a design from a diff of model_a and model_b
        
        id should be a string with no spaces (conversion handled)
        
        Returns the saved design diff

        :param model: cobrapy model
        :param did: design identifier
        :param name: name of the design
        :param description: text description of what it does
        :param conditions: conditions that should be applied for the design
        :param base_model: Model that the design should be derived from - specified model included in project
        :param parent: string for parent design that this design is a diff from
        :param overwrite: overwrite and existing design (only applies if the id is already in use)
        """
        # Test, infeasible designs should not be added
        status = model.solver.optimize()
        if status == 'infeasible':
            raise Infeasible('Could not find valid solution')

        if parent is not None:
            if isinstance(parent, string_types):
                parent = self.get_design(parent)
            elif not isinstance(parent, StrainDesign) or parent.id not in self.list_designs:
                raise DesignError('Parent relate a valid project strain design')

        did = str(did).replace(' ', '_')
        design_save_path = os.path.join(self.design_path, '{}.json'.format(did))

        if os.path.exists(design_save_path) and not overwrite:
            raise IOError('File {} exists'.format(design_save_path))

        if base_model is None and parent is None:
            base_model = self.config.default_model
        elif parent is not None:
            # If a parent design is specified this model is loaded first
            base_model = parent.base_model
        elif base_model is not None and base_model not in self.config.models:
            raise KeyError('Base model not found should be one of {}'.format(" ".join(self.config.models)))

        if parent is None:
            lmodel = self.load_model(base_model)
        else:
            lmodel = parent.load()

        if conditions is not None:
            self.load_conditions(conditions, lmodel)

        # Find all the differences between the models
        diff = model_diff(lmodel, model)

        if parent is not None:
            parent = parent.id

        diff['description'] = description
        diff['id'] = did
        diff['name'] = name
        diff['conditions'] = conditions
        diff['base_model'] = base_model
        diff['parent'] = parent

        des = StrainDesign.from_dict(did, diff, self)
        des.to_json(design_save_path, overwrite=overwrite)

        return des

    def load_diff(self, diff, base_model=None):
        """ Take a diff dictionary and add it to a model (does not require saving a design file) """
        diff['description'] = 'tmp diff loaded'
        diff['id'] = 'tmp_design_diff'
        diff['name'] = 'tmp_design_diff'
        diff['conditions'] = None
        diff['base_model'] = base_model
        diff['parent'] = None
        tmp_design = StrainDesign.from_dict('tmp_design', diff, self)
        return tmp_design.load()

    @property
    def list_conditions(self):
        conditions_store = self.get_conditions(update=True)
        return list(conditions_store["growth_conditions"].keys())

    def load_conditions(self, conditions_id, model=None, copy=False):
        """
        Load a model with a given set of pre-saved media conditions
        :param conditions_id: identifier of conditions file
        :param model: string or cobrapy model
        :param copy: return copy of model or modify inplace
        :return:
        """

        conditions_store = self.get_conditions(update=True)
        cx = conditions_store['growth_conditions'][conditions_id]

        if model is None or isinstance(model, string_types):
            mdl = self.load_model(model)
        elif copy:
            mdl = model.copy()
        else:
            mdl = model

        load_medium(mdl, cx['media'])
        if "carbon_source" in cx and cx["carbon_source"] is not None:
            # Will throw error if invalid transporter
            c_tx = mdl.reactions.get_by_id(cx["carbon_source"])
            c_tx.upper_bound = c_tx.lower_bound

        return mdl

    def add_essential_pathway(self, tid, reactions, description='', reaction_fluxes=None,
                              models=None, designs=None, conditions=None, overwrite=False):
        """
        Add a pathway to automated testing to confirm reactions are always present in model and the pathway always
        carries flux.

        This is just a simpler way of adding essential pathways than manually adding a json file with the same
        information.

        :param tid:
        :param reactions:
        :param description:
        :param reaction_fluxes:
        :param models:  If None, only the default model is checked unless at least one design is specified
        :param designs:  By default designs are never checked. specifying all tests the pathway on all designs
        :param conditions:  None, by default. Specifies the conditions which a pathway is present in.
        :param overwrite:
        :return:
        """

        if not isinstance(tid, str):
            raise TypeError('Identifier must be a string')

        if isinstance(models, str) and models != "all":
            raise TypeError('Models must specify \'all\', be a list of valid models or None (default model only)')

        if designs is None:
            designs = []

        if conditions is None:
            conditions = []

        if models is None and len(self.designs) == 0:
            models = [self.config.default_model]

        elif models is None:
            models = []

        if reaction_fluxes is None:
            reaction_fluxes = dict()

        test_file = os.path.join(os.path.abspath(self.tests_dir), 'test_{}.json'.format(tid))
        # Check if the test identifier exists or not
        if os.path.exists(test_file) and not overwrite:
            raise IOError('Test of the same id already exists. Must specify unique id.')

        test = dict(
            conditions=conditions,
            models=models,
            designs=designs,
            reaction_fluxes=reaction_fluxes,
            required_reactions=reactions,
            description=description,
        )

        # Validate models, designs, conditions actually exist

        if designs != 'all':
            for did in designs:
                if did not in self.list_designs:
                    raise KeyError('Design {} not found'.format(did))

        if models != 'all':
            for mid in models:
                if mid not in self.config.models:
                    raise KeyError('Model {} not found'.format(mid))

        if conditions != 'all':
            for cid in conditions:
                if cid not in self.conditions['growth_conditions']:
                    raise KeyError('Conditions {} not found'.format(cid))

        # Save the json test file to disk.
        with open(test_file, 'w+') as tf:
            json.dump(test, tf)

    def growth_condition(self, conditions_id):
        conditions_store = self.get_conditions(update=True)
        return conditions_store['growth_conditions'][conditions_id]['observe_growth']

    def save_conditions(self, model, conditions_id, carbon_source=None, apply_to=None, observe_growth=True):
        """
        Add media conditions that a given model has to the project. Essentially the lower bounds on transport reactions.
        All other trnasport reactions will be switched off.

        In some cases, one may wish to set conditions under which a model should not grow.
        observe_growth allows this to be configured. If using a single model or if the condition should not grow under
        any circumstances, observe_growth can be set to false.

        If certain models should grow, specify this with a a tuple where the entries refer to the model files tracked by
        the project. All models specified must be contained within the project.

        :param model: cobrapy model
        :param conditions_id: identifier for the conditions should be unique
        :param carbon_source: name of carbon source in the media that has a fixed uptake rate
        :param apply_to: iterable of models that this set of designs applies to
        :param observe_growth: bool or list.
        :return:
        """
        # If it can't get a solution then this will raise errors.
        status = model.solver.optimize()
        if not observe_growth and status != 'infeasible':
            raise AssertionError('Model should not grow')
        elif observe_growth and status == 'infeasible':
            raise Infeasible('Cannot find valid solution - should conditions result in growth?')

        if apply_to is None:
            apply_to = []
        elif not isinstance(apply_to, list):
            apply_to = [apply_to]

        for mdl_path in apply_to:
            if mdl_path not in self.config.models:
                raise KeyError("Model {} not in current project".format(mdl_path))

        # List all transport reactions in to the cell
        def is_exchange(rr):
            return (len(rr.reactants) == 0 or len(rr.products) == 0) and len(rr.metabolites) == 1

        def is_media(rr):
            if rr.lower_bound < 0 and is_exchange(rr):
                return True
            return False
        
        media = {}
        for r in model.reactions:
            if is_media(r):
                media[r.id] = r.lower_bound
        
        # save to conditions file
        conditions_store = self.get_conditions(update=True)

        if carbon_source is not None and carbon_source not in media:
            raise KeyError("carbon source not valid")

        conditions_store['growth_conditions'][conditions_id] = dict(
            media=media,
            designs=apply_to,
            observe_growth=observe_growth,
            carbon_source=carbon_source,
        )
        self._write_conditions(conditions_store)

    def _write_conditions(self, conditions_store):
        """
        Writes updated conditions store
        TODO: Validate passed dictionary
        TODO: make this a persistent dict stored in memory?
        :param conditions_store:
        :return:
        """
        with self.project_context_lock:
            with open(self._conditions_file, 'w+') as cf:
                json.dump(conditions_store, cf, indent=4)

    @classmethod
    def create_project(cls, models, description, author, author_email, project_path):
        """
        Creates new projects

        :param models: iterable of models can be strings to path locations or cobra model instances.
        :param description: String description of project
        :param author: string author names, separate with &
        :param author_email: email of project owner. separate with ';'
        :param project_path: location on disk to place project. Must not contain existing gsmodutils project.
        :return:
        """
        configuration = dict(
            description=description,
            author=author,
            author_email=author_email
        )

        cfg = ProjectConfig(**configuration)
        cfg.create_project(project_path, addmodels=models)

        return cls(project_path)
