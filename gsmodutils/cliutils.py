"""
This module contains the main command line interface for project creation, testing and handling
"""
from __future__ import absolute_import, division, generators, print_function, nested_scopes, with_statement

import json
import os

import click
import cobra

from gsmodutils.exceptions import ProjectNotFound
from gsmodutils.model_diff import model_diff


def load_project(project_path):
    from gsmodutils.project import GSMProject
    project = None
    try:
        project = GSMProject(project_path)
    except ProjectNotFound:
        click.echo('Error project not found in path'.format(project_path))
        exit()

    return project


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
    project = load_project(project_path)
    tester = project.project_tester()
    # Collect list of tests
    click.echo('Collecting tests...')
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

        if verbose:
            click.echo("verbose mode, showing successes and failures")
            click.echo()

        print('Running tests: ', end='')
        for _ in tester.iter_tests(skip_default=skip_default):
            print('.', end='')
        click.echo()
        ts = 0
        te = 0
        for tf, log in tester.log.items():

            if tf == 'default_tests':
                click.echo('Default project file tests (models, designs, conditions):')
                indicator = "Project file"
            else:
                click.echo("Test file {}:".format(tf))
                indicator = "Test file"
            lc = log.log_count
            ts += lc[0]
            te += lc[1]
            click.echo("Counted {} test assertions with {} failures".format(*lc))
            # Output base test file
            if not log.is_success:
                click.echo(click.style('{} has errors'.format(indicator), fg='red'))
            else:
                click.echo(click.style('{} completed all tests without error'.format(indicator), fg='green'))
            
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
        # display tests with indentations for test files/casesand
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
@click.argument('project_path', type=click.Path(writable=True))
@click.argument('model_path', type=str, default=None)
def create_project(project_path, model_path):
    """Create a new gsmodutils project"""
    from gsmodutils.project_config import ProjectConfig
    click.echo('Project creation {}'.format(project_path))

    click.echo('Using mode {}'.format(project_path))

    description = click.prompt('Please enter a project description', type=str)
    author = click.prompt('Author name', type=str)
    author_email = click.prompt('Author email', type=str)

    configuration = dict(
            description=description,
            author=author,
            author_email=author_email
    )
    
    # TODO: find out how to add multiple paths with click
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
@click.argument('model_path')
@click.option('--base_model', default=None, help='Project model to compare with')
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--parent', default=None, help='A parent design')
@click.option('--output', default=None, help='A location to output the diff as a sjon file')
@click.option('--names/--no-names', default=True, help='Output names of added or changed metabolites and reactions')
def diff(model_path, base_model, project_path, parent, output, names):
    """ View the changed reactions between a model and a base model """

    import cameo

    project = load_project(project_path)
    base_model = project.load_model(base_model)
    if parent is not None:
        base_model = project.load_design(parent, base_model)

    nmdl = cameo.load_model(model_path)

    click.echo('Comparing models...')
    mdiff = model_diff(base_model, nmdl)
    click.echo('new model has {} removed reactions'.format(len(mdiff['removed_reactions'])))
    click.echo('new model has {} added or changed reactions'.format(len(mdiff['reactions'])))

    click.echo('new model has {} removed metabolites'.format(len(mdiff['removed_metabolites'])))
    click.echo('new model has {} added or changed metabolites'.format(len(mdiff['metabolites'])))

    if names:

        if len(mdiff['removed_reactions']):
            click.echo('Removed reactions:')

        for reaction in mdiff['removed_reactions']:
            click.echo('\t {}'.format(reaction))

        if len(mdiff['reactions']):
            click.echo('Added or changed reactions:')

        for reaction in mdiff['reactions']:
            click.echo('\t {} - {}'.format(reaction['id'], reaction['name']))

        if len(mdiff['removed_metabolites']):
            click.echo('Removed metabolites:')

        for metabolite in mdiff['removed_metabolites']:
            click.echo('\t {}'.format(metabolite))

        if len(mdiff['metabolites']):
            click.echo('Added or changed metabolites:')

        for metabolite in mdiff['metabolites']:
            click.echo('\t {} - {}'.format(metabolite['id'], metabolite['name']))

    if output is not None:
        with open(output, 'w+') as outfile:
            json.dump(mdiff, outfile)


@click.command()
@click.argument('path')
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--diff', default=True, help='Make sure model is unique to this project')
@click.option('--validate/--no-validate', default=True, help='Chose to validate the model before it is added.')
def add_model(path, project_path, diff, validate):
    """Add a model to a specified gsm project"""
    load_project(project_path)
    # Check the diff between other models
    if diff:
        pass

    project = None
    try:
        project.add_model(path, validate=validate)
    except KeyError:
        click.echo(click.style('Model of the same naem already included in project', fg='red'))
        exit()

    click.echo('Model successfully added to project')


@click.command()
@click.argument('model_path')
@click.argument('identifier')
@click.option('--name', default=None, help='Formal design name (longer than identifier)')
@click.option('--description', default=None, help='Description of what the design does')
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--parent', default=None, help='A parent design that was applied first to avoid replication.')
@click.option('--base_model', default=None, help='Model that design is based on')
@click.option('--overwrite/--no-overwrite', default=False, help='overwrite existing design')
@click.option('--from-diff/--not-from-diff', default=False, help='load a diff file instead of compatible model')
def dimport(model_path, identifier, name, description, project_path, parent, base_model, overwrite, diff):
    """ Import a design into a model. This can be new or overwrite an existing design. """

    project = load_project(project_path)
    if diff:
        with open(model_path) as diff_file:
            df = json.load(diff_file)
            # model_path is a json diff file
            model = project.load_diff(df, base_model=base_model)
    else:
        import cameo
        model = cameo.load_model(model_path)
    # Check if the design already exists
    new = True
    if identifier in project.list_designs and not overwrite:
        click.echo('Error: Design {} already exists. Use --overwrite to replace'.format(identifier))
        exit()
    elif identifier in project.list_designs:
        new = False

    if parent is not None and parent not in project.list_designs:
        click.echo('Error: Parent design {} does not exist'.format(parent))
        exit()

    if name is None and new:
        name = click.prompt('Please enter a name for this design', type=str)

    if description is None and new:
        description = click.prompt('Please enter a description for this design', type=str)

    project.save_design(model, identifier, name=name, description=description, parent=parent, base_model=base_model,
                        overwrite=overwrite)

    click.echo('Design successfully added to project')


@click.command()
@click.argument('path')
@click.argument('ident')
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--apply_to', default=None, help='Description of what the design does')
@click.option('--growth/--no_growth', default=True, help='Should these conditions allow growth or not')
def iconditions(path, ident, project_path, apply_to, growth):
    """ Add a given set of media condtions from a model (this ignores any added or removed reactions or metabolites)"""
    import cameo
    model = cameo.load_model(path)
    project = load_project(project_path)
    project.save_conditions(model, ident, apply_to=apply_to, observe_growth=growth)


_output_fmts = ('json', 'yaml', 'sbml', 'matlab', 'mat', 'm', 'scrumpy', 'spy')


@click.command()
@click.argument('file_format', default=None, type=click.Choice(_output_fmts))
@click.argument('filepath')
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--model_id', default=None, help='model id')
@click.option('--conditions', default=None, help='conditions to apply')
@click.option('--design', default=None, help='design to apply')
@click.option('--overwrite/--no-overwrite', default=False, help='model id')
def export(file_format, filepath, project_path, model_id, design, conditions, overwrite):
    """ Export a given model with a specific design and conditions applied """
    if os.path.exists(filepath) and not overwrite:
        click.echo('error - {} already exists. Must use overwrite option'.format(filepath))
        exit()

    project = load_project(project_path)
    model = project.load_model(model_id)

    if conditions is not None:
        project.load_conditions(model=model, conditions_id=conditions)
    # always load designs last
    if design is not None:
        model = project.load_design(design, model)

    if file_format == 'json':
        cobra.io.save_json_model(model, filepath, pretty=True)
    elif file_format in ['spy', 'scrumpy']:
        click.echo('Scrumpy exports are currently not implemented.')
        exit()
    elif file_format in ['matlab', 'm', 'mat']:
        cobra.io.save_matlab_model(model, filepath)
    elif file_format == 'yaml':
        cobra.io.save_yaml_model(model, filepath)
    elif file_format == 'sbml':
        cobra.io.write_sbml_model(model, filepath)

    click.echo('Model {} successfully written'.format(filepath))


@click.command()
@click.option('--project_path', default='.', help='gsmodutils project path')
def info(project_path):
    """ Display all the information about a gsmodutils project (list models, paths, designs etc. """
    project = load_project(project_path)
    click.echo('''--------------------------------------------------------------------------------------------------
Project description - {description}
Author(s): - {author}
Author email - {author_email}
Designs directory - {design_dir}
Tests directory - {tests_dir}   
    '''.format(**project.config.to_save_dict()))

    click.echo("Models:")
    for mdl_path in project.config.models:
        model = project.load_model(mdl_path)
        click.echo("\t* {}".format(mdl_path))
        click.echo("\t\t {}".format(model.id))
        click.echo("\t\t {}".format(model.description))

    click.echo("Designs:")
    for d in project.designs:
        design = project.get_design(d)
        click.echo("\t* {}".format(design.id))
        click.echo("\t\t {}".format(design.name))
        click.echo("\t\t {}".format(design.description))
        if design.parent is not None:
            click.echo("\t\t Parent: {}".format(design.parent.id))

    click.echo("Conditions:")
    for c in project.conditions['growth_conditions']:
        click.echo("\t* {}".format(c))
    click.echo('''--------------------------------------------------------------------------------------------------''')


cli.add_command(test)
cli.add_command(add_model)
cli.add_command(export)
cli.add_command(dimport)
cli.add_command(create_project)
cli.add_command(info)
cli.add_command(diff)
cli.add_command(iconditions)

if __name__ == "__main__":
    cli()
