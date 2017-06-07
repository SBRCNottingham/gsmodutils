from __future__ import print_function, absolute_import, division
from gsmodutils.exceptions import ProjectConfigurationError, ProjectNotFound
import gsmodutils
import hglib
import cobra
import os
import shutil
import json

_default_project_file = '.gsmod_project.json'
_default_model_conditionsfp = 'model_conditions.json'
_templates_path = os.path.join(
    os.path.dirname( os.path.abspath(gsmodutils.__file__)), 'templates')


class ProjectConfig(object):
    '''
    Class for configuration
    Takes configuration arguments and ensures that the required configuration options are included
    
    Validates configuration and then creates the project directory etc
    '''
    _required_cfg_params = [
            'description', 'author', 'author_email', 'models', 
            'repository_type', 'conditions_file', 'tests_dir',
            'design_dir', 'default_model',
        ]
    
    def __init__(self, **kwargs):
        # Just loads the configuration
        loaded_cfg_params = [x.lower() for x in kwargs.keys()]
        # Check required options are there
        for it in self._required_cfg_params:
            if it not in loaded_cfg_params:
                raise ProjectConfigurationError('Project configuration option "{}" is missing'.format(it) )
        
        for arg, val in kwargs.items():
            setattr(self, arg.lower(), val)

    
    def _to_save_dict(self):
        '''
        Could possibly just use self.__dict__ but this is the set of configuration options
        '''
        return dict( [ (it, getattr(self, it)) for it in self._required_cfg_params ] )
    
    
    def _create_docker_file(self, path, dockerfile_name='Dockerfile'):
        '''
        Create a default docker container for running a model in test container
        Users may want to modify this for their own purposes, for now this is just a simple way of running the tests and generating a report
        '''
        # Create the dockerfile
        df_path = os.path.join(_templates_path, 'Dockerfile')
        dockerfile_path = os.path.join(path, dockerfile_name)
        shutil.copy(df_path, dockerfile_path)
        
        # Create the requirements file
        reqs_path = os.path.join(_templates_path, 'requirements.txt')
        dt_path = os.path.join(path, 'requirements.txt')
        shutil.copy(reqs_path, dt_path)
            
        return dockerfile_path


    def _create_deafault_tests(self, path):
        '''
        Creates a default test folder
        '''
        tpl_path = os.path.join(_templates_path, 'default_tests.tpy')
        
        new_path = os.path.join(path, 'tests', 'test_model.py')
        
        shutil.copy(tpl_path, new_path)
        
        return new_path


    def _create_empty_conditions_file(self, project_path):
        conditions_fp = os.path.join(project_path, _default_model_conditionsfp)
        
        if os.path.exists(conditions_fp):
            raise ProjectConfigurationError('A conditions file already exists {}'.format(conditions_fp) )
        
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
    
    
    def _save_config(self, project_path):
        configuration_fp = os.path.join(project_path, _default_project_file)

        with open(configuration_fp, 'w+') as configf:
            json.dump(self._to_save_dict(), configf, indent=4)
        
        return configuration_fp
    

    def create_project(self, project_path, addmodels=[], validate=True, docker=True):
        '''
        Checks if project config is valid and creates a project if it is
        This function tries to clean up after itself when errors occur
        
        Add models assumes the absolute path to models
        
        If you add multiple models, the default model is the first path specified
        '''
        
        project_path = os.path.abspath(project_path)
        created = False
        
        # Create directory that doesn't exist
        if not os.path.exists(project_path):
            created = True
            os.mkdir(os.path.join(project_path))
        
        # We can import existing 
        if os.path.exists(os.path.join(project_path, _default_project_file)):
            raise ProjectConfigurationError( 'configuration file {} already exists'.format(_default_project_file) )
        
        added_directories = []
        added_files = []
        
        try:
            # Create a mercurial repo if there isn't an existing one
            try:
                hglib.init(project_path)
                # For removal if there is an error in a directory that exists without a mercurial repo
                added_directories.append(os.path.join(project_path , '.hg'))
            except hglib.error.CommandError:
                # We can work with an existing mercurial project if its there
                # This might create some errors for users
                pass
            
            repository = hglib.open(project_path)
            
            # create the folder stcuture
            tests_directory = os.path.join(project_path, self.tests_dir)
            
            if not os.path.exists(tests_directory):
                os.mkdir(tests_directory)
                added_directories.append(tests_directory)
            
            designs_directory =  os.path.join(project_path, self.design_dir) 
            
            if not os.path.exists(designs_directory):
                os.mkdir(designs_directory)
                added_directories.append(designs_directory)
            
            if not len(addmodels):
                # Create a new empty model
                mdl_path = os.path.abspath( 
                        os.path.join(project_path, 'model.json') )
                
                newmodel = cobra.Model()
                newmodel.id = 'mdl0'
                newmodel.description = 'Changeme - auto created model for new gsm project'
                
                cobra.io.save_json_model(newmodel, mdl_path)
                self.models.append('model.json')
                added_files.append(mdl_path)
            
            
            for mdl_path in addmodels:
                mdl_path = os.path.abspath(mdl_path)
                cpy_path = os.path.abspath( 
                        os.path.join(project_path, os.path.basename(mdl_path)) )
                
                if not os.path.exists(mdl_path):
                    raise IOError('No such model file exists {}'.format(mdl_path))
                
                # copy model file to repository (if not already there)
                if cpy_path != mdl_path:
                    shutil.copy(mdl_path, cpy_path)
                    added_files.append(cpy_path) # to delete copied files, not existing ones
                
                # Add the model to the configuration
                self.models.append( os.path.basename(mdl_path) )
                repository.add(cpy_path)
            
            
            self.default_model = self.models[0]

            configuration_fp = self._save_config(project_path)
            added_files.append(configuration_fp)
            repository.add(configuration_fp)
            
            
            conditions_fp = self._create_empty_conditions_file(project_path)
            added_files.append(conditions_fp)
            repository.add(conditions_fp)
            
            if docker:
                docker_image_path = self._create_docker_file(project_path)
                added_files.append(docker_image_path)
                repository.add(docker_image_path)
            
            # Adding tests folder
            tests = self._create_deafault_tests(project_path)
            repository.add(tests)
            
            repository.commit('Initial commit for model, auto generated commit by gsm_project.py')
            
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
