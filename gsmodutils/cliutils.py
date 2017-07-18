"""
This module contains the main command line interface for project creation, testing and handling
"""
from __future__ import absolute_import, division, generators, print_function, nested_scopes, with_statement
import os
import json
import click

from gsmodutils.exceptions import ProjectNotFound


@click.group()
def cli():
    """Command line tools for management of gsmodutils projects"""
    pass


def _output_child_logs(log, verbose=False, indent=4, baseindent=4):
    """
    Outputs logs with indentations and counts the total number of tests and errors
    """
    idt = " "*indent
    for cid, clog in log.children.items():
        style = 'red'
        if clog.is_success:
            style = 'green'
        
        click.echo(
                click.style(idt + "--" + str(clog.id), fg=style)
        )
        for msg, desc in clog.error:
            click.echo(
                click.style(idt + "Asserion error: " + msg, fg='red')
            )
            
        if verbose:
            for msg, desc in clog.success:
                click.echo(
                    click.style(idt + "Asserion success: " + msg, fg='green')
                )
            
        _output_child_logs(clog, verbose=verbose, indent=indent+baseindent)

        if verbose and log.std_out is not None:
            click.echo("-------- Captured standard output ----------")
            click.echo(log.std_out)
            click.echo("-------- End standard output ----------")
        click.echo()
        

@click.command()
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--display_only/--run_tests', default=False, help='Just show found tests, does not run')
@click.option('--test_id', default=None, help='specify a given test identifier to run - pyton filename, function or' +
                                              'json_filename entry')
@click.option('--skip_default/--no_skip_default', default=False, help='skip default tests')
@click.option('--verbose/--no_verbose', default=False, help='Dispalty succesfully run test assertions')
@click.option('--log_path', default=None, type=click.Path(writable=True), help='path to output json test log')
def test(project_path, test_id, display_only, skip_default, verbose, log_path):
    """Run tests for a project"""
    # TODO: individual test files
    click.echo('Collecting tests...')
        
    from gsmodutils.project import GSMProject
    try:
        project = GSMProject(project_path)
        tester = project.project_tester()
    except ProjectNotFound: 
        click.echo(
            click.style('Error: gsmodutils project not found in this path', fg='red')
        )
        exit()

    # Collect list of tests
    tester.collect_tests()
    
    # Display errors
    for tf, e in tester.load_errors:
        click.echo(
            click.style('Error loading test {} \n {}'.format(tf, e), fg='red')
        )
    
    for tf, e in tester.syntax_errors.items():
        click.echo(
            click.style('Error - {} has syntax errors {}'.format(tf, e), fg='red')
        )
    
    for tf, entry_key, missing_fields in tester.invalid_tests:
        click.echo(
            click.style('---Error with formating of test {} in {} ---'.format(tf, entry_key), fg='yellow')
        )
        
        click.echo('Missing fields:')
        for field in missing_fields:
            click.echo('\t{}'.format(field))
    
    if test_id is not None:
        test_id = tuple(test_id.split(" "))
        
        if len(test_id) == 1:
            test_id = test_id[0]
        # Only run specific test id
        if test_id not in tester.tests:
            click.echo(
                click.style('Test {} not found'.format(test_id), fg='red')
            )
            click.echo("Tests to select from: \n\t" + "\n\t".join(tester.tests))
        else:
            log = tester.run_by_id(test_id)
            click.echo("results for {}".format(log.id))
            # run test, get log
            _output_child_logs(log)
        
        exit()
    
    barstr = "-"*25
    if not display_only:
        # TODO Progress bar as tests are run
        click.echo(
            click.style(barstr + ' gsmodutils test results ' + barstr, bg='green', bold=True)
        )

        # TODO: flag for skipping default test runs
        if verbose:
            click.echo("verbose mode, showing successes and failures")
            click.echo()
        
        with click.progressbar(tester.iter_tests(skip_default=skip_default), label='Running tests: ') as bar:
            for x in bar:
                pass
        
        ts = 0
        te = 0
        for tf, log in tester.log.items():

            if tf == 'default_tests':
                click.echo('Default project tests:')
                for ki, val in log.children.items():
                    click.echo("{} {}".format(len(val.error), len(val.success)))
            else:
                click.echo("Test file {}:".format(tf))
            lc = log.log_count
            ts += lc[0]
            te += lc[1]
            click.echo("Counted {} test assertions with {} failures".format(*lc))
            # Output base test file
            if not log.is_success:
                click.echo(click.style('Test file has errors', fg='red'))
            else:
                click.echo(click.style('Test file completed all tests without error', fg='green'))
            
            # Count total tests, count total assertions
            _output_child_logs(log, verbose=verbose)
            
            if log.std_out is not None:
                click.echo(
                    click.style(barstr + ' Captured standard output ' + barstr, fg='black', bg='white')
                )
                click.echo(log.std_out)
                click.echo(
                    click.style(barstr + ' End standard output ' + barstr, fg='black', bg='white')
                )         
        click.echo(
            'Ran {} test assertions with a total of {} errors ({}% success)'.format(ts, te, ((ts-te)/ts) * 100)
        )
        
        # Save report to json log file
        if log_path is not None:
            try:
                with open(log_path, 'w+') as lf:
                    json.dump(tester.to_dict(), lf, indent=4)
            except IOError:
                click.echo(
                    click.style('Error writing log file'.format(log_path), fg='red')
                )
            except TypeError:
                click.echo(
                    click.style('Error writing log file, tests appear to be in nonstandard' +
                                'format. Check executable python test files', fg='red')
                )
                
    else:
        click.echo(
            click.style(barstr + ' TESTS FOUND ' + barstr, fg='green')
        )
        # display tests with indentations for test files/cases
        json_tests, py_tests = tester.tests
        for id_key in json_tests:
            click.echo('JSON test file - {}'.format(id_key))
            for entry_key in json_tests[id_key]:
                click.echo('\t{}'.format(entry_key))
    
        for id_key in py_tests:
            click.echo('Executable test file - {}'.format(id_key))
            for entry_key in py_tests[id_key]:
                click.echo('\t{}'.format(entry_key))


@click.command()
@click.option('--project_path', type=click.Path(writable=True), help='new gsmodutils project path')
@click.option('--model_path', type=str, default=None, help='path to a given model')
def create_project(project_path, model_path):
    """Create a new gsmodutils project"""
    from gsmodutils.project_config import ProjectConfig
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


@click.command()
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--model_id', default=None, help='Base model id')
@click.option('--conditions', default=None, help='conditions to apply')
@click.option('--design', default=None, help='design to apply')
@click.option('--filepath', default=None, help='output filename')
@click.option('--format', default=None, help='output to smbl, json, matlab format')
def export(project_path, model_id, design, conditions, filepath, file_format):
    """ Export a given model with a specific design and conditions applied """
    pass

@click.command()
def info():
    """ 
    Display all the information about a gsmodutils project (list models, paths, designs etc.
    """
    pass
    

cli.add_command(test)
cli.add_command(create_project)


