# Genome scale model development framework.
Initially developed by the Nottingham SBRC for use with their genome scale models.

Design goals:
* Portability and interoperability:
models come in different formats - cobra JSON, matlab, SBML, ScrumPy etc. The tool needs to be able to export and
import models in these formats. This allows users to leverage tools not just in the python development stack, such
as CobraPy but also other strain design methods from the likes of Matlab and OptKnock. This is achieved through
a command line api that allows the export of files in to a variety of formats. This ensures that good standards
can be followed and maintained.

* Reusability of previous designs
The constraints, reactions, genes and metabolites for different designs can be a headache to manage. Generally, a
base strain will exist and users will modify this over a long period of time. Likewise, designs the exploit existing
hetrologous pathways or optimisations can be reused through an inherited design approach.

* Testability of models
The validity of a model is a difficult aspect to measure. Constant manual curation in order to match experimental
data requires users to check conditions. For this reason a testing framework is adopted allowing models to maintain
conditions of validation. By default added growth constraints and designs can be tested. Users can also write tests
in python and JSON to ensure that essential pathways are maintained and validation against experimental data is met.

* Sharability
The design of the project uses flat files rather than database systems. Whilst this looses some power it ensures
that any models developed can be shared easily through distributed source control software like Git
and mercurial. Similarly, in the future the project aims to allow models to be distributed via Docker containers
allowing controlled environments to improve collabortation where users require more than just a model to perform
complex analysis.


## Installation

(TODO) To install the latest release from pip:

    pip install gsmodutils

To install this software clone the git repository and type:

    pip install -r requriements.txt
    python setup.py install
    
To run the tests for this project, install pytest and, from the project root directory simply run

    pytest
    
gsmodutils is fully compatible with python 2.7+ and python 3.5+.
(TODO) Software has been tested on linux (Ubuntut, manjaro/arch), windows and MacOSX. 

## gsm_project
Main script is gsm_project; this creates new genome scale model projects given an SBML or JSON file. This creates a folder structre in location with name specified.

* An initial mercruial repository is created with a first commit message.
* Dockerfile is created for the model which can be executed to run model inside of. Install dependencies upon first usage.
* Design directory for storing json designs of the genome scale model
* Initial test scripts are written which can be refined with py.test following the full user guide on tool usage.
* Creates test substrates/pathways json file for automated grows/can't grow tests
* Asks for a project description file and creats this
* Mercurial hooks for pre-commits that run tests and create testing reports


## parse_scrumpy
Parse scrumpy is a tool that allows a user to create COBRA JSON models from scrumpy but has some requirements.
Note that this script is heavily experimental and only really tested with Nottingham's cupriavidus model. It should parse any model correctly but setting constraints requires a json file with fixed transporter fluxes.
The flux for the ATPase reaction is also required. As most large scrumpy models are built from  metacyc/biocyc, this is assumed


## Library utitlities

Projects:

To be coded more fully.

using the gsmodutils.project.Project class one can interface with the project.

This functionality will include the following:

Creating, loading and adding designs

Very nice feature - storing saves as part of the repository commit process
    - This will be tricky because it means checking to see if there are uncommited changes
    - This could be a mode that is switched on or off by the user and throws errors whenever uncommited changes exist asking the user to handle this

Load designs.
Run tests on different models/designs
tests will automatically load a project and run tests inside of it
This means a design can be loaded and tests compared against design a and design b


## Dependencies
python
python-pip
if using docker, docker is required to be installed and configured. 

## Design Problems to resolve 
Updating things between versions of this software - what if we add new configuration options? what if structure of project changes?

Test cases - default test cases should be part of the software, maybe include a __version__ check on the template test cases?


## Command line utilities
### scrumpy_to_cobra (done)
Takes a scrumpy (structural!) model and converts it to a cobra compatable model (so you don't need scrumpy installed).
BIG TODO - have this work with minimisation of reaction fluxes objective function in cobrapy/cameo based models

### cobra_to_scrumpy (todo, if needed)
Create a scrumpy model from a cobrapy model

### gsmodutils create_project (complete)
creates a new project

### gsmodutils test (partially complete)
Run executable and json tests

### gsmodutils export (todo)
Export a model with a given design/conditions in a specified format (json, scrumpy, sbml-cobra or matlab)

### gsmodutils import_model (todo)
add a model file to a project

### gsmodutils import_design (todo)
Take a model file and create a design from the diff between it and a specified base model

### gsmodutils import_conditions (todo)
Specify json conditions file or a model with transporters set (other changes will be ignored) and add it to the set of conditions stored for the project

### gsmodutils create_image (todo)
Create a docker image of the project in its current state. This image can be run on any system with docker installed making the model and tests portable
    
## TODO

* Model diff reports - human readable
* Test reports - human readable
* Command line utilities as interface to all of project

* logging


* Unit tests for module
    - model diff (done)
    - project creation (done)
    - saving designs (done)
    - config changes
    - Docker files work (This one is hard to make general)
* Full test coverage
    
    
* Mercurial commit hooks when models in the project change
* User guide
* Scripts for starting docker etc

## Future features
Comparing diffed models to metanetx common database of reactions

* Map two models from different sources to the database
* Show reactions maintained between different models and differences between each other
* Show reactions not contained in the database
* Show where reactions partially, but not fully, match the database
    
Better design for executable tests
* pull out descriptions from python files
* figure out a way to list all tests 


## See also

This project would be nothing without other great open source software projects.
In particular, we would like to draw attention to ```cameo``` and ```cobrapy```.
These projects offer a wide array of functionality for FBA and other constraints based
analysis within the python open source stack.


## Contributors
James Gilbert  University of Nottingham - main software developer.
Nicole Pearcy - Testing, ideas and knowledge of genome scale models.

If you would like to collaborate, please get in touch!