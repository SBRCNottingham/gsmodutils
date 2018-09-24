from __future__ import print_function

import click
import json
import os

import cobra
import re

from gsmodutils.utils import StringIO


class ParseError(Exception):
    pass


def load_scrumpy_model(filepath_or_string, name=None, model_id=None, media=None, objective_reactions=None,
                       obj_dir='min', fixed_fluxes=None):
    """
    Specify a base scrumpy structural model file and returns a cobra model.
    This hasn't be thoroughly tested so expect there to be bugs

    To get a solution from the returned object you need to specify nice stuff like the atpase reaction and media

    :param filepath_or_string: filepath or scrumpy string
    :param name:
    :param model_id:
    :param media:
    :param objective_reactions:
    :param obj_dir:
    :param fixed_fluxes:
    :return:
    """

    if objective_reactions is None:
        objective_reactions = ['Biomass']

    if fixed_fluxes is not None:
        assert isinstance(fixed_fluxes, dict)

    if os.path.isfile(filepath_or_string):
        rel_path = '/'.join(os.path.abspath(filepath_or_string).split('/')[:-1])
        fp = os.path.abspath(filepath_or_string).split('/')[-1]
        reactions, metabolites, externals = parse_file(fp, rel_path=rel_path)
    else:
        rel_path = '.'
        reactions, metabolites, externals = parse_string(filepath_or_string, rel_path=rel_path)

    model = cobra.Model()
    for mid in metabolites:
        compartment = 'e'
        if mid[:2] == "x_" or mid in externals:
            compartment = 'e'
        m = cobra.Metabolite(id=mid, compartment=compartment)  # ScrumPy does not use compartments
        model.add_metabolites([m])

    added_reactions = []
    for reaction in reactions:
        if reaction['id'] not in added_reactions:
            r = cobra.Reaction(reaction['id'])
            model.add_reactions([r])
            r.lower_bound = reaction['bounds'][0]
            r.upper_bound = reaction['bounds'][1]
            r.add_metabolites(reaction['metabolites'])
            added_reactions.append(reaction['id'])

    # We need to add transporters for external metabolites not defined with the "External" directive
    for metabolite in model.metabolites:
        if metabolite.id[:2] == "x_":
            r = cobra.Reaction("EX_{}".format(metabolite.id[2:]))
            model.add_reactions([r])
            r.lower_bound = -1000.0
            r.upper_bound = 1000.0
            r.add_metabolites({
                metabolite.id: -1.0
            })
            added_reactions.append(r.id)

    if media is not None:
        for ex_reaction in model.exchanges:
            ex_reaction.lower_bound = media.get(ex_reaction.id, 0)

    if fixed_fluxes is not None:
        for rid, flux in fixed_fluxes.items():
            try:
                reaction = model.reactions.get_by_id(rid)
                reaction.lower_bound = flux
                reaction.upper_bound = flux
            except KeyError:
                click.echo('Error setting fixed flux for reaction id {}, not found'.format(rid))

    for oreact in objective_reactions:
        try:
            objreac = model.reactions.get_by_id(oreact)
            objreac.objective_coefficient = 1.0
        except KeyError:
            print('Error setting objective, reaction name {} not found'.format(oreact))
    
    model.objective.direction = obj_dir

    model.id = model_id
    model.name = name
    return model


def get_tokens(line):
    """
    Goes through each charachter in scrumpy file attempting to find tokens

    FIXME: if there is a numeric after a direction token this fails
    e.g. '->2 "PROTON"' fails but '-> 2 "PROTON"' works
    :param line_dt:
    :return:
    """

    line_dt = line.strip().split('#')[0]

    tokens = []
    quoted = False
    tk_str = ""
    line_dt = line_dt.replace("->", "-> ")
    line_dt = line_dt.replace("<-", "<- ")
    line_dt = line_dt.replace("<>", "<> ")
    
    for ch in line_dt:
        if ch in ['"', "'"]:
            if not quoted:
                quoted = True
                if len(tk_str) and ch != " ":
                    tokens.append(tk_str)
                tk_str = ch
            elif tk_str[0] == ch:
                tk_str += ch
                tokens.append(tk_str)
                tk_str = ""
                quoted = False
            else:
                tk_str += ch
                
        elif ch in ["(", ")", ":", ",", " "] and not quoted:
            if len(tk_str):
                tokens.append(tk_str)
            tk_str = ""
            if ch != " ":
                tokens.append(ch)
        else:
            tk_str += ch
    
    if len(tk_str):
        tokens.append(tk_str)
            
    return tokens


def parse_file(filepath, fp_stack=None, rel_path=''):
    """
     Recursive function - takes in a scrumpy spy file and parses it, returning a set of reactions

    Note this code is not fully tested. Expect some bugs.
    :param filepath:
    :param fp_stack:
    :param rel_path:
    :return:
    """
    if fp_stack is None:
        fp_stack = [filepath]
    else:
        fp_stack.append(filepath)

    with open(os.path.join(rel_path, filepath)) as infile:
        reactions, metabolites, externals = parse_fobj(infile, fp_stack, rel_path, filepath)
    return reactions, metabolites, externals


def parse_string(spy_string, rel_path='.'):
    with StringIO() as fstr:
        fstr.write(spy_string)
        fstr.seek(0)
        reactions, metabolites, externals = parse_fobj(fstr, [], rel_path, "scrumpy_string")
    return reactions, metabolites, externals


def parse_fobj(infile, fp_stack, rel_path, source_name):

    num_match = re.compile("[0-9]*/[0-9]*")
    reactions = []
    metabolites = []
    externals = []

    in_include = False
    in_external = False
    in_reaction = False
    s_coef = -1
    si = 1.0

    for linecount, line in enumerate(infile):
        # Ignore anything after comments
        tokens = get_tokens(line)
        prev_token = ''
        # print tokens
        for token in tokens:
            if in_reaction:

                if token == '~':
                    in_reaction = False
                    s_coef = -1
                    reactions.append(reaction)
                elif token in ["<-", "<>", "->"]:
                    s_coef = 1
                    if token == "<-":
                        reaction['bounds'] = [-1000.0, 0.0]
                    elif token == "->":
                        reaction['bounds'] = [0.0, 1000.0]
                    else:
                        reaction['bounds'] = [-1000.0, 1000.0]

                elif token == "+":
                    pass
                else:
                    try:
                        si = float(token)
                    except ValueError:

                        if num_match.match(token):
                            si = eval(token)
                        elif len(token.strip()):
                            metab = token.replace('"', '').replace("'", '')

                            metabolites.append(metab)
                            # not a stoichiometric value
                            reaction['metabolites'][metab] = s_coef * si
                            si = 1.0

                prev_token = token
                continue

            if in_external:
                if token in [',', '(']:
                    continue
                elif token == ')':
                    in_external = False
                else:
                    token = token.replace('"', '')
                    metabolites.append(token)
                    externals.append(token)
                    rs = dict(
                        id='{}_tx'.format(token),
                        metabolites={token: -1.0},
                        source=source_name,
                        bounds=[-1000.0, 1000.0]
                    )

                    reactions.append(rs)

                continue

            if in_include:

                if token in [',', '(']:
                    continue

                elif token == ')':
                    in_include = False
                elif token in fp_stack:
                    raise ParseError('Cyclic dependency for file {}'.format(token))
                else:
                    rset, mset, exset = parse_file(token, fp_stack, rel_path)
                    reactions += rset
                    metabolites += mset
                    externals += exset
                continue

            if token == 'External':
                in_external = True

            elif token == 'Include':
                in_include = True
            elif token == ":":
                in_reaction = True
                s_coef = -1
                reaction = dict(
                    source=source_name,
                    metabolites={},
                    id=prev_token.replace('"', '').replace("'", ""),
                    line=linecount,
                )

            prev_token = token

    return reactions, metabolites, externals


@click.command()
@click.argument('model')
@click.argument('model_id')
@click.option('--name', default=None, help='Specify a name for this model')
@click.option('--output', default='omodel.json', help='output location for json file')
@click.option('--media', default=None, type=str, help='A growth media constraints file')
@click.option('--fixed_fluxes', default=None, help='Path to a json dictionary containing biomass composition')
@click.option('--objective', default='Biomass', help='Objective reaction id')
@click.option('--objective_direction', default='min', help='objective direction (min or max)')
def scrumpy_to_cobra(model, model_id, name, output, media, fixed_fluxes, objective,
                     objective_direction):
    """
    Command line utility for parsing scrumpy files and creating cobrapy models

    By default, models use the minimisation of flux objective function approach, though if a lumped biomass reaction
    is present, this can be specified as a maximisation objective.

    For the minimisation of fluxes approach a biomass composition should be specified.
    This should be a json file of fixed biomass transporter reaction identifiers and their associated flux value.

    If the lumped biomass reaction is used the media composition will be required for growth.
    These values are the lower bounds for the fluxes on uptake reactions.
    """
    if fixed_fluxes is not None and os.path.exists(fixed_fluxes):
        with open(fixed_fluxes) as mp:
            fixed_fluxes = json.load(mp)
    else:
        fixed_fluxes = None

    if media is not None and os.path.exists(media):
        with open(media) as mp:
            media = json.load(mp)
    else:
        media = None

    model = load_scrumpy_model(model,
                               media=media, 
                               objective_reactions=[objective],
                               obj_dir=objective_direction,
                               fixed_fluxes=fixed_fluxes,
                               name=name,
                               model_id=model_id
                               )

    cobra.io.save_json_model(model, output)
