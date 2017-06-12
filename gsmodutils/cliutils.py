import argparse
import os
import json

def scrumpy_to_cobra():
    import cobra
    from gsmodutils.scrumpy import load_scrumpy_model
    
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
