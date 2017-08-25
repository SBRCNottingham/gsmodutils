from __future__ import print_function, absolute_import, division

import json
import os
import shutil

import cobra

import gsmodutils
from gsmodutils.exceptions import ProjectConfigurationError
from gsmodutils.utils.validator import validate_model_file

default_project_file = '.gsmod_project.json'
default_model_conditionsfp = 'model_conditions.json'
default_designsfp = 'designs'
default_testsfp = 'tests'
_templates_path = os.path.join(
    os.path.dirname(os.path.abspath(gsmodutils.__file__)), 'templates')


class ProjectConfig(object):
    
    _cfg_params = [
        'description', 'author', 'author_email', 'tests_dir', 'design_dir', 'conditions_file',
        'repository_type', 'default_model', 'models',
    ]
    
    def __init__(self, description, author, author_email, **kwargs):
        """
        Class for configuration
        Takes configuration arguments and ensures that the required configuration options are included

        Validates configuration and then creates the project directory.
        :param kwargs: has required fields - description, author, author_email
        """
        # always sets param defaults first
        self.tests_dir = default_testsfp
        self.design_dir = default_designsfp
        self.conditions_file = default_model_conditionsfp
        self.repository_type = None
        self.default_model = None
        self.models = []

        self.author = author
        self.description = description
        self.author_email = author_email

        # used for the optional config parameters
        for arg, val in kwargs.items():
            setattr(self, arg.lower(), val)

    def to_save_dict(self):
        """
        Could possibly just use self.__dict__ but this is the set of configuration options
        """
        return dict([(it, getattr(self, it)) for it in self._cfg_params])

    @staticmethod
    def create_docker_file(path, dockerfile_name='Dockerfile'):
        """
        Create a default docker container for running a model in test container
        Users may want to modify this for their own purposes, for now this is just a simple way of running the tests
        and generating a report

        args:
        """
        # Create the dockerfile
        df_path = os.path.join(_templates_path, 'Dockerfile')
        dockerfile_path = os.path.join(path, dockerfile_name)
        shutil.copy(df_path, dockerfile_path)

        # Create the requirements file
        reqs_path = os.path.join(_templates_path, 'requirements.txt')
        dt_path = os.path.join(path, 'requirements.txt')
        shutil.copy(reqs_path, dt_path)

        return dockerfile_path

    @staticmethod
    def _create_empty_conditions_file(project_path):
        conditions_fp = os.path.join(project_path, default_model_conditionsfp)

        if os.path.exists(conditions_fp):
            raise ProjectConfigurationError('A conditions file already exists {}'.format(conditions_fp))

        # empty conditions configuration
        conditions = dict(
            substrates=dict(),
            pathways=dict(),
            carbon_sources=dict(),
            growth_conditions=dict(),

        )

        with open(conditions_fp, 'w+') as conditionsf:
            json.dump(conditions, conditionsf, indent=4)

        return conditions_fp

    def save_config(self, project_path):
        """
        
        args:
            project_path (str) path to save the configuration
        """
        configuration_fp = os.path.join(project_path, default_project_file)

        with open(configuration_fp, 'w+') as configf:
            json.dump(self.to_save_dict(), configf, indent=4)

        return configuration_fp

    def create_project(self, project_path, addmodels=None, validate=True, docker=True):
        """
        Checks if project config is valid and creates a project if it is
        This function tries to clean up after itself when errors occur
        
        Add models assumes the absolute path to models
        
        If you add multiple models, the default model is the first path specified
        
        args:
            project_path (str) valid path to create project in
            addmodels (list, optional) paths to models that are added to the project
            validate (bool, optional) validate models to be added to the project
            docker (bool, optional) create a docker file for this project (can be done at a later time)
        """
        
        project_path = os.path.abspath(project_path)
        created = False
        
        # Create directory that doesn't exist
        if not os.path.exists(project_path):
            created = True
            os.mkdir(os.path.join(project_path))
        
        # We can import existing 
        if os.path.exists(os.path.join(project_path, default_project_file)):
            raise ProjectConfigurationError('configuration file {} already exists'.format(default_project_file))
        
        added_directories = []
        added_files = []

        if addmodels is None:
            addmodels = []

        try:
            # create the folder stcuture
            tests_directory = os.path.join(project_path, self.tests_dir)
            
            if not os.path.exists(tests_directory):
                os.mkdir(tests_directory)
                added_directories.append(tests_directory)
            
            designs_directory = os.path.join(project_path, self.design_dir)
            
            if not os.path.exists(designs_directory):
                os.mkdir(designs_directory)
                added_directories.append(designs_directory)
            
            if not len(addmodels):
                # Create a new empty model
                mdl_path = os.path.abspath( 
                        os.path.join(project_path, 'model.json'))
                
                newmodel = cobra.Model()
                newmodel.id = 'mdl0'
                
                cobra.io.save_json_model(newmodel, mdl_path)
                self.models.append('model.json')
                added_files.append(mdl_path)
            
            for mdl_path in addmodels:

                if isinstance(mdl_path, cobra.Model):
                    if mdl_path.id in [" ", ""]:
                        raise NameError("Passed model without identifier, cannot write to disk")

                    # write new model object to disk
                    save_path = os.path.abspath(os.path.join(project_path, mdl_path.id + ".json"))
                    cobra.io.save_json_model(mdl_path, save_path, pretty=True)
                    mdl_path = save_path
                else:
                    mdl_path = os.path.abspath(mdl_path)
                    cpy_path = os.path.abspath(
                            os.path.join(project_path, os.path.basename(mdl_path)))

                    if not os.path.exists(mdl_path):
                        raise IOError('No such model file exists {}'.format(mdl_path))

                    if validate:
                        vcheck = validate_model_file(mdl_path)
                        if len(vcheck['errors']):
                            raise ProjectConfigurationError('Invalid model {}'.format(mdl_path))

                    if cpy_path != mdl_path:
                        shutil.copy(mdl_path, cpy_path)
                        added_files.append(cpy_path)  # to delete copied files, not existing ones
                
                # Add the model to the configuration
                self.models.append(os.path.basename(mdl_path))

            self.default_model = self.models[0]

            configuration_fp = self.save_config(project_path)
            added_files.append(configuration_fp)
            
            conditions_fp = self._create_empty_conditions_file(project_path)
            added_files.append(conditions_fp)

            if docker:
                docker_image_path = self.create_docker_file(project_path)
                added_files.append(docker_image_path)

        except:
            # Cleanup after ourselves upon failure - i.e. don't create a new project
            # This flag is important - the code should never delete an existing user space!
            if created:
                shutil.rmtree(project_path)
            else:
                for dp in added_directories:
                    shutil.rmtree(dp)
                
                for fp in added_files:
                    if os.path.exists(fp):
                        os.remove(fp)
                    
            raise
