"""
This module contains the main command line interface for project creation
"""
from __future__ import absolute_import, division, generators, print_function, nested_scopes, with_statement
import os
import json
import click

from gsmodutils.project_config import ProjectConfig
from gsmodutils.exceptions import ProjectNotFound, ProjectConfigurationError


@click.group()
def cli():
    """Command line tools for management of gsmodutils projects"""
    pass

@click.command()
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--test', default=None, help='run specific test cases')
def test(project_path, test):
    """Run tests for a project"""
    
    from gsmodutils.project import GSMProject
    try:
        project = GSMProject(project_path)
    except ProjectNotFound: 
        click.echo(
            click.style('Error: gsmodutils project not found in this path', fg='red')
        )
        exit()
        
    tester = project.project_tester()
    # If user specific test, load just this test (if it exists)
    
    # 
    
@click.command()
@click.option('--project_path', type=click.Path(writable=True), help='new gsmodutils project path')
@click.option('--model_path', type=str, default=None, help='path to a given model')
def create_project(project_path, model_path):
    """Create a new gsmodutils project"""
    click.echo('Project creation {}'.format(project_path))

    click.echo('Using mode {}'.format(project_path))

    add_models = []

    description = click.prompt('Please enter a project description', type=unicode)
    author = click.prompt('Author name', type=unicode)
    author_email = click.prompt('Author email', type=str)

    configuration = dict(
            description=description,
            author=author,
            author_email=author_email
    )
    
    # TODO: find out how to add multple path
    add_models = [model_path]
    if model_path is None:
        # Create a new model
        click.confirm('No model specified, create new model?', abort=True)
        click.echo(
            click.style('Empty model file model.json will be created', fg='green')
        )
        add_models = []
    
    # Actually create the project
    try:
        click.echo('creating project in {}'.format(os.path.abspath(project_path)))
        cfg = ProjectConfig(**configuration)
        cfg.create_project(project_path, addmodels=add_models)

        click.echo(
            click.style('Project created succesfully', fg='green')
        )
    except Exception as ex:
        click.echo(
            click.style('Project creation error', fg='red')
        )
        click.echo(
            click.style('{}'.format(ex), fg='red')
        )
        
        
@click.command()
def model_diff(model_a=None, model_b=None, revision=None):
    """
    Create a diff report of two models
    """
    
    click.echo('')

@click.command()
def add_model():
    pass

@click.command()
def add_design():
    pass

@click.command()
def add_conditions():
    pass

@click.command()
def add_test_case():
    pass

cli.add_command(test)
cli.add_command(create_project)
