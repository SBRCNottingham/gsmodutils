from __future__ import print_function
import os
import argparse
import json
import cobra
from cameo.core.utils import load_medium


def load_scrumpy_model(filepath, atpase_reaction="ATPase", atpase_flux=3.0,
                       media=None, objective_reactions=None, obj_dir='max'):
    """
    Specify a base scrumpy structural model file and returns a cameo model.
    This hasn't be thoroughly tested so expect there to be bugs
    
    To get a solution from the returned object you need to specify nice stuff like the atpase reaction and media
    """

    if objective_reactions is None:
        objective_reactions = ['Biomass']

    if media is None:
        media = {}

    rel_path = '/'.join(os.path.abspath(filepath).split('/')[:-1])

    reactions, metabolites = parse_file(os.path.abspath(filepath).split('/')[-1], rel_path=rel_path)
    model = cobra.Model()
    for mid in metabolites:
        m = cobra.Metabolite(id=mid)
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
    
    for metabolite in model.metabolites:
        if metabolite.id[:2] == "x_":
            metabolite.remove_from_model()
    
    for exch in model.exchanges:
        # flip stoichiometric stoichiometric coef
        mset = {}
        
        for met in exch.metabolites:
            mset[met] = -1 * exch.metabolites[met]
            
        exch.clear_metabolites()
        exch.add_metabolites(mset)
        
        if exch.id not in media:
            exch.lower_bound = 0
            exch.upper_bound = 1000
        else:
            exch.lower_bound = -1000
            exch.upper_bound = 1000

    load_medium(model, media)
    
    try:
        atpase = model.reactions.get_by_id(atpase_reaction)
        atpase.lower_bound = atpase_flux
        atpase.upper_bound = atpase_flux
    except KeyError:
        print('Error setting ATPase flux, reaction name {} not found'.format(atpase_reaction))
    
    for oreact in objective_reactions:
        
        try:
            objreac = model.reactions.get_by_id(oreact)
            objreac.objective_coefficient = 1.0
        except KeyError:
            print('Error setting objective, reaction name {} not found'.format(oreact))
    
    model.objective.direction = obj_dir
    
    return model


def get_tokens(line_dt):
    """
    Goes through each charachter in scrumpy file attempting to find tokens
    
    BUG: if there is a numeric after a direction token this fails
    e.g. '->2 "PROTON"' fails but '-> 2 "PROTON"' works
    """
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
    
    This code is not that stable. Expect bugs.
    """
    if fp_stack is None:
        fp_stack = []

    reactions = []
    metabolites = []
    with open(rel_path+'/'+filepath) as infile:
        
        in_include = False
        in_external = False
        in_reaction = False
        s_coef = -1
        si = 1.0
        
        for linecount, line in enumerate(infile):
            # Ignore anything after comments
            line_dt = line.strip().split('#')[0]
            
            tokens = get_tokens(line_dt)
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
                            
                            metab = token.replace('"', '').replace("'", '')
                            if metab[:2] != "x_":
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
                        rs = dict(
                            id='{}_tx'.format(token),
                            metabolites={token: 1.0},
                            source=filepath,
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
                        raise Exception('Cyclic dependency for file {}'.format(token))
                    else:
                        rset, mset = parse_file(token, fp_stack + [filepath], rel_path)
                        reactions += rset
                        metabolites += mset
                    continue

                if token == '':
                    continue
                
                elif token == 'External':
                    in_external = True
                    
                elif token == 'Include':
                    in_include = True
                elif token == ":":
                    in_reaction = True
                    s_coef = -1
                    reaction = dict(
                        source=filepath,
                        metabolites={},
                        id=prev_token.replace('"', '').replace("'", ""),
                        line=linecount,
                    )

                prev_token = token

    return reactions, metabolites


def scrumpy_to_cobra():
    
    # Parser argument
    parser = argparse.ArgumentParser(description='parse a scrumpy file and output a json cobra compatable model')
   
    parser.add_argument('--model', required=True, action="store",
                        help='Path to the main scrumpy model')
    
    parser.add_argument('--output', default='omodel.json', action="store",
                        help='output location for json file')
    
    parser.add_argument('--media', default='default_media.json', action='store')
    
    parser.add_argument('--atpase_reaction', default="ATPase", action="store")
    parser.add_argument('--atpase_flux', default=3.0, type=float)
    
    parser.add_argument('--objective_reaction', default='Biomass')
    parser.add_argument('--objective_direction', default='max', action="store")
    
    args = parser.parse_args()
    
    if os.path.exists(args.media):
        media = json.load(open(args.media))
    else:
        media = dict()
    
    if len(media) == 0:
        print("No media transport reactions found, model will not grow")
   
    model = load_scrumpy_model(args.model,
                               atpase_reaction=args.atpase_reaction,
                               atpase_flux=args.atpase_flux,
                               media=media, 
                               objective_reactions=[args.objective_reaction],
                               obj_dir=args.objective_direction)

    cobra.io.save_json_model(model, args.output)
