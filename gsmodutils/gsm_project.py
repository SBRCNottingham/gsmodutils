#!/usr/bin/python
from __future__ import absolute_import, division, generators, unicode_literals, print_function, nested_scopes, with_statement
import argparse
import os
from gsmodutils.validator import validate_model_file
import json
import shutil
import hglib

default_requirements = [
    'ipython',
    'cameo',
    'cobra',
    #gsmodutils - need to set up pip first,
]


def create_docker_image(path, dockerfile_name='Dockerfile', requirements=default_requirements):
    '''
    Create a default docker container for running a model in test container
    Users may want to modify this for their own purposes, for now this is just a simple way of running the tests and generating a report
    '''
    dockerfile_path = path + '/' + dockerfile_name
    
    tpl = '''

    '''
    
    with open(dockerfile_path, 'w+') as df:
        df.write(tpl)
    
    # Create the requirements file
    
    requirements_file_path = path + '/requirements.txt'
    with open(requirements_file_path, 'w+') as rp:
        for requirement in requirements:
            rp.write(req + "\n")
        
    return dockerfile_path


def create_deafault_tests(path):
    '''
    '''
    pass


def create_commit_hooks(path):
    '''
    '''
    pass


def create_project(args):
    project_path = os.path.abspath(args.path)
    
     # Check that the folder doesn't already exist
    if os.path.exists(project_path):
        print('Error - {} file or folder already exists'.format(project_path))
        return 
    
    # If the user specifies a model but it isn't found
    if args.model is not None and not os.path.exists(args.model):
        print('Error specified model file not found')

    if args.validate:
        validation_check = validate_model_file(args.model)
        
        for error in validation_check['errors']:
            print("Model error: ", error)
        
        if args.warnings:
            for warning in validation_check['warnings']:
                print("Model warning: ", warning)
        
        if len(validation_check['errors']):
            print('Errors found in model, aborting. To force repository creation use --no-validation option')
            return

    # Try to create the root folder
    try:
        os.mkdir(project_path)
    except OSError:
        print('Error - creating folder structure for model. It is likely that this path does not exist or you cannot write to it.')
        return
    
    description = raw_input('Enter a description for this project: ')
    author = raw_input('Full name of author: ')
    email = raw_input('Email address of author: ')


    try:
        hglib.init(project_path)
        repository = hglib.open(project_path)
        # create the folder stcuture
        os.mkdir(project_path + '/tests/')
        os.mkdir(project_path + '/designs/')
        
        if args.model is not None:
            # copy model file to repository
            model_fp = os.path.basename(args.model)
            shutil.copy(args.model, project_path + '/' + model_fp)
        else:
            import cobra
            # create a brand new model
            model_fp = 'model.json'
            m = cobra.Model()
            m.description = description
            cobra.io.save_json_model(m, project_path + '/' + model_fp)
        
        repository.add(project_path + '/' + model_fp)
        
        configuration_fp = project_path + '/.gsmod_project.json'
        conditions_fp = project_path + '/model_conditions.json'

        # Project configuration file
        configuration = dict(
            description=description,
            author=author,
            author_email=email,
            default_model=model_fp,
            repository_type='hg',
        )
        
        
        # empty conditions configuration
        conditions = dict(
            substrates=dict(),
            pathways=dict(),
            carbon_sources=dict(),
            growth_conditions=dict(),
        )
        
        with open(configuration_fp, 'w+') as configf:
            json.dump(configuration, configf, indent=4)
            
        repository.add(configuration_fp)
        
        with open(conditions_fp, 'w+') as conditionsf:
            json.dump(conditions, conditionsf, indent=4)
            
        repository.add(conditions_fp)
        
        if args.docker:
            docker_image_path = create_docker_image(project_path)
            repository.add(docker_image_path)
        
        repository.commit('Initial commit for model, auto generated commit by gsm_project.py')
        
        print('Project created successfully. Refer to gsmodutils user guide for proper usage.')
    except Exception as e:
        # Cleanup after ourselves upon failure
        shutil.rmtree(project_path)
        raise e
    


def main():
    '''
    Handles command line arguments
    '''
    parser = argparse.ArgumentParser(description='Create a mercurial repository for a genome scale metabolic model and handle design and management through test driven behaviour')
    
    parser.add_argument('--model', default=None, action="store",
                        help='Path to the cobra/sbml model (json or sbml) if left blank one will be created')
     
    parser.add_argument('--name', required=True, action='store', help='Name of the genome scale model')
    
    parser.add_argument('--no-validation', dest='validate', action='store_false', 
                        help='Switch of model validation - allow creation with a model that isn\'t currently validated')
    
    parser.add_argument('--path', required=True, action='store', help='Path to create repository in (must not exist already)')
     
    
    parser.add_argument('--print-warnings', dest='warnings', action='store_true', 
                        help='Print warnings from model validation check')
    
    parser.add_argument('--docker', action='store_true', help='create a docker file for the project')
    
    parser.set_defaults(validate=True)
    args = parser.parse_args()
    create_project(args)
    
    
if __name__ == "__main__":
    main()