"""
This module contains the main command line interface for project creation, testing and handling
"""
from __future__ import absolute_import, division, generators, print_function, nested_scopes, with_statement

import json
import os

import click
import cobra

from gsmodutils.exceptions import ProjectNotFound, ValidationError, DesignError, DesignOrphanError
from gsmodutils.model_diff import model_diff
from gsmodutils import GSMProject, load_model
from gsmodutils.project.project_config import ProjectConfig
from sys import exit


def _load_project(project_path):
    project = None
    try:
        project = GSMProject(project_path)
    except ProjectNotFound:
        click.echo('Error project not found in path'.format(project_path))
        exit(-1)

    return project


@click.group()
def cli():
    """Command line tools for management of gsmodutils genome scale model projects"""
    pass  # pragma: no cover


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
                click.style(idt + "Asserion error: {}".format(msg), fg='red')
            )

        for msg, desc in clog.warnings:
            click.echo(
                click.style(idt + "Warning: {}".format(msg), fg='yellow')
            )

        if verbose:
            for msg, desc in clog.success:
                click.echo(
                    click.style(idt + "Assertion success: {}".format(msg), fg='green')
                )
            
        _output_child_logs(clog, verbose=verbose, indent=indent+baseindent)

        if verbose and log.std_out not in [None, "", " "]:
            click.echo("-------- Start standard output ----------")
            click.echo(log.std_out)
            click.echo("-------- End standard output ----------")
        click.echo()
        

@click.command()
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--test_id', default=None, help='specify a given test identifier to run - pyton filename, function or' +
                                              'json_filename entry')
@click.option('--skip_default/--no_skip_default', default=False, help='skip default tests')
@click.option('--verbose/--no_verbose', default=False, help='Dispalty succesfully run test assertions')
@click.option('--log_path', default=None, type=click.Path(writable=True), help='path to output json test log')
def test(project_path, test_id, skip_default, verbose, log_path):
    """Run tests for a project"""
    project = _load_project(project_path)
    tester = project.project_tester()
    # Collect list of tests
    click.echo('Collecting tests...')
    tester.collect_tests()

    if test_id is not None:
        # Only run specific test id
        if test_id not in tester.test_ids:
            click.echo(
                click.style('Test {} not found'.format(test_id), fg='red')
            )
            click.echo("Tests to select from: \n\t" + "\n\t".join(tester.test_ids))
            exit(-1)
        else:
            log = tester.run_by_id(test_id)
            click.echo("results for {}".format(log.id))
            # run test, get log
            _output_child_logs(log, verbose=verbose)
        
        exit(0)
    
    barstr = "-"*25

    click.echo(
        click.style(barstr + ' gsmodutils test results ' + barstr, bg='green', bold=True)
    )

    if verbose:
        click.echo("verbose mode, showing successes and failures")
        click.echo()

    click.echo('Running tests: ')
    tester.progress_tests(skip_default=skip_default)
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
            click.echo(click.style('{} has test errors'.format(indicator), fg='red'))
        else:
            click.echo(click.style('{} completed all tests without error'.format(indicator), fg='green'))

        # Count total tests, count total assertions
        _output_child_logs(log, verbose=verbose)

        if log.std_out not in [None, "", " "]:
            click.echo(
                click.style(barstr + ' Captured standard output ' + barstr, fg='black', bg='white')
            )
            click.echo(log.std_out)
            click.echo(
                click.style(barstr + ' End standard output ' + barstr, fg='black', bg='white')
            )
    percent = round(((ts - te) / ts) * 100, 3)
    click.echo('Ran {} test assertions with a total of {} errors ({}% success)'.format(ts, te, percent))

    # Display errors
    for tf, e in tester.load_errors:
        click.echo(
            click.style('Error loading test {} \n {}'.format(tf, e), fg='red')
        )

    for tf, e in tester.syntax_errors.items():
        click.echo(
            click.style('Error - {} has syntax errors {}'.format(tf, e), fg='red')
        )

    for tf, entry_key, exception in tester.invalid_tests:
        click.echo(
            click.style('---Error with formating of test {} in {} ---'.format(tf, entry_key), fg='yellow')
        )

        click.echo('\tError found in file:')
        click.echo('\t{}'.format(exception.message))

    # Save report to json log file
    if log_path is not None:
        with open(log_path, 'w+') as lf:
            json.dump(tester.to_dict(), lf, indent=4)
            click.echo('log file written to {}'.format(log_path))


@click.command()
@click.argument('project_path', type=click.Path(writable=True))
@click.argument('default_model_path', type=click.Path(exists=True))
@click.option('--name', prompt='Project name')
@click.option('--description', prompt='Please enter a project description', help='Project description')
@click.option('--author', prompt='Author name', help='Project name')
@click.option('--email', prompt='Please enter author email', help='Author email')
@click.option('--add_models', multiple=True, type=click.Path(exists=True), help='paths to additional model files,'
                                                                                ' separated by space')
@click.option('--validate/--skip_validation', default=True, help='Require the model to be validated')
def init(project_path, default_model_path, name, description, author, email, add_models, validate):
    """Create a new gsmodutils project"""
    click.echo('Project creation {}'.format(project_path))
    click.echo('Using model {}'.format(default_model_path))

    configuration = dict(
            name=name,
            description=description,
            author=author,
            author_email=email
    )

    # Make sure we only try and add models once. Click confirms valid path, config validates models
    add_models = list(set([default_model_path] + list(add_models)))

    # Actually create the project
    try:
        click.echo('Creating project in {}'.format(os.path.abspath(project_path)))
        cfg = ProjectConfig(**configuration)
        cfg.create_project(project_path, addmodels=add_models, validate=validate)

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
        exit(-1)


@click.command()
@click.argument('model_path')
@click.option('--base_model', default=None, help='Project model to compare with')
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--parent', default=None, help='A parent design')
@click.option('--output', default=None, help='A location to output the diff as a sjon file')
@click.option('--names/--no-names', default=True, help='Output names of added or changed metabolites and reactions')
def diff(model_path, base_model, project_path, parent, output, names):
    """ View the changed reactions between a model and a base model """
    project = _load_project(project_path)
    base_model = project.load_model(base_model)
    if parent is not None:
        base_model = project.load_design(parent, base_model)

    nmdl = load_model(model_path)

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
@click.argument('path', type=click.Path(exists=True))
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--validate/--no-validate', default=True, help='Chose to validate the model before it is added.')
def addmodel(path, project_path, validate):
    """
    Add a model to a specified gsm project.
    If validation is selected, where the model fails to conform to cobra standards, the model will not be added to the
    project.
    """
    project = _load_project(project_path)
    try:
        project.add_model(path, validate=validate)
    except ValidationError:
        click.echo(click.style('Model does not appear to be valid, use no-validate option if you would'
                               'still like to continue', fg='red'))
        exit(-1)
    except KeyError:
        click.echo(click.style('Model of the same name already included in project', fg='red'))
        exit(-1)

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
@click.option('--from_diff/--not_from_diff', default=False, help='load a diff file instead of compatible model')
def dimport(model_path, identifier, name, description, project_path, parent, base_model, overwrite, from_diff):
    """ Import a design into a model. This can be new or overwrite an existing design. """

    project = _load_project(project_path)
    try:
        if from_diff:
            with open(model_path) as diff_file:
                df = json.load(diff_file)
                # model_path is a json diff file

                model = project.load_diff(df, base_model=base_model)
        else:
            model = load_model(model_path)
    except ValidationError as exp:
        click.echo('Validation Error with design: {}'.format(exp))
        exit(-1)

    # Check if the design already exists
    new = True
    if identifier in project.list_designs and not overwrite:
        click.echo('Error: Design {} already exists. Use --overwrite to replace'.format(identifier))
        exit(-2)
    elif identifier in project.list_designs:
        new = False

    if parent is not None and parent not in project.list_designs:
        click.echo('Error: Parent design {} does not exist'.format(parent))
        exit(-3)

    if name is None and new:
        name = click.prompt('Please enter a name for this design', type=str)

    if description is None and new:
        description = click.prompt('Please enter a description for this design', type=str)

    try:
        project.save_design(model, identifier, name=name, description=description, parent=parent, base_model=base_model,
                            overwrite=overwrite)
    except ValidationError as exp:
        click.echo('Validation Error with design: {}'.format(exp))
        exit(-4)

    click.echo('Design successfully added to project')


@click.command()
@click.argument('path')
@click.argument('ident')
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--apply_to', default=None, help='Description of what the design does')
@click.option('--growth/--no_growth', default=True, help='Should these conditions allow growth or not')
def iconditions(path, ident, project_path, apply_to, growth):
    """ Add a given set of media condtions from a model (this ignores any added or removed reactions or metabolites)"""
    model = load_model(path)
    project = _load_project(project_path)
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
        exit(-1)

    project = _load_project(project_path)
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
        exit(-1)
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
    project = _load_project(project_path)

    click.echo("-" * click.get_terminal_size()[0])
    click.echo('''Project description - {description}
Author(s): - {author}
Author email - {author_email}
Designs directory - {design_dir}
Tests directory - {tests_dir}   
    '''.format(**project.config.to_save_dict()))

    click.echo("Models:")
    for mdl_path in project.config.models:
        try:
            model = project.load_model(mdl_path)
            click.echo(click.style("\t* {}".format(mdl_path), fg="green"))
            click.echo("\t\t {}".format(model.id))
        except Exception as exp:
            click.echo(click.style("\t* {} Error loading".format(mdl_path), fg="red"))
            click.echo("\t\t {}".format(exp))

    click.echo("Designs:")
    for d in project.list_designs:

        click.echo("*" * click.get_terminal_size()[0])
        try:
            design = project.get_design(d)
        except DesignError as exp:
            click.echo(click.style("\t* Error loading design {} {} ".format(d, exp), fg="red"))
            continue
        except DesignOrphanError:
            click.echo(click.style("\t* Appears to be problem with parent of design {}".format(d), fg="red"))
            continue
        except ValidationError as exp:
            click.echo(click.style("\t* Error validating design {} {}".format(d, exp), fg="red"))
            continue

        click.echo(click.style("\t* {} {}".format(design.name, design.id), fg="green"))

        if design.parent is not None:
            click.echo("\tParent: {}".format(design.parent.id))

        click.echo("\t\t{}".format(design.description))

    click.echo("*" * click.get_terminal_size()[0])
    click.echo("Conditions:")
    for c in project.conditions['growth_conditions']:
        click.echo("\t* {}".format(c))

    if not len(project.conditions['growth_conditions']):
        click.echo(click.style("\t\tNo growth conditions found"))
    click.echo("-" * click.get_terminal_size()[0])


@click.command()
@click.option('--project_path', default='.', help='gsmodutils project path')
@click.option('--overwrite/--no-overwrite', default=False, help='overwrite existing dockerfile')
@click.option('--build/--no-build', default=False, help='build docker container')
@click.option('--save/--no-save', default=False, help='save docker image of tagged container')
@click.option('--tag', default=None, help='tag name for docker container (appended to project name).')
@click.option('--save_path', default=None, help='Save path for shared docker image')
def docker(project_path, overwrite, build, save, tag, save_path):
    """ Create a dockerfile for the project """
    project = _load_project(project_path)
    if os.path.exists(os.path.join(project_path, 'Dockerfile')) and not overwrite:
        click.echo('**** A Dockerfile already exists, use --overwrite to replace **** \n')
    else:
        project.config.create_docker_file(project_path)
        click.echo('**** Created Dockerfile **** \n')

    # Check to see if docker is installed on the machine
    import docker
    from docker.errors import APIError, BuildError, ImageNotFound
    client = docker.from_env()
    try:
        client.info()
    except ConnectionError:  # pragma: no cover
        click.echo(  # pragma: no cover
            click.style('Error: Docker is either not installed or not configured on your system'
                        'please consult the documentation at docs.docker.com', fg='red')
        )
        exit(-1)  # pragma: no cover

    ttag = project.config.name
    if tag is not None:
        ttag += ":" + tag

    ttag = ttag.lower()

    if not build:
        click.echo('Build option not specified use "gsmodutils docker --build"'
                   'or "docker build -t=\'{}\'" to build a container.'.format(project.config.name))
    else:
        click.echo('Running docker build, this may take some time...')
        try:
            client.images.build(path=project.project_path, tag=ttag)
            click.echo('Image built')

        except BuildError as e:  # pragma: no cover
            click.echo(  # pragma: no cover
                click.style('Error building project:\n{}'.format(e), fg='red')
            )

        except APIError as e:  # pragma: no cover
            click.echo( # pragma: no cover
                click.style('Docker returned an error:\n{}'.format(e), fg='red')
            )
            exit(-1)  # pragma: no cover

    if save:
        # ensure that build has been completed first
        image = None  # pragma: no cover
        try:  # pragma: no cover
            image = client.images.get(ttag)  # pragma: no cover
        except ImageNotFound:  # pragma: no cover
            click.echo(  # pragma: no cover
                click.style('Image not found try building image first', fg='red')
            )
            exit(-1)  # pragma: no cover
        except APIError as e:  # pragma: no cover
            click.echo(  # pragma: no cover
                click.style('Docker returned an error:\n{}'.format(e), fg='red')
            )  # pragma: no cover
            exit(-1)  # pragma: no cover

        if save_path is None:  # pragma: no cover
            save_path = os.path.join(project.project_path, ttag + '.tar')  # pragma: no cover

        click.echo('Writing docker image to path {}. This may take some time...'.format(save_path))  # pragma: no cover

        try:  # pragma: no cover
            resp = image.save()  # pragma: no cover
            with open(save_path, 'w+') as image_tar:  # pragma: no cover
                for chunk in resp.stream():  # pragma: no cover
                    image_tar.write(chunk)  # pragma: no cover

        except APIError as e:  # pragma: no cover
            click.echo(  # pragma: no cover
                click.style('Docker returned an error:\n{}'.format(e), fg='red')  # pragma: no cover
            )
            exit(-1)  # pragma: no cover


cli.add_command(test)
cli.add_command(addmodel)
cli.add_command(export)
cli.add_command(dimport)
cli.add_command(init)
cli.add_command(info)
cli.add_command(diff)
cli.add_command(iconditions)
cli.add_command(docker)
