# gsmodutils - a genome scale model development and testing framework.
Initially developed by the Nottingham SBRC for use with their genome scale models.

Design goals:

* **Portability and interoperability**:
models come in different formats - cobra JSON, matlab, SBML, ScrumPy etc. The tool needs to be able to export and
import models in these formats. This allows users to leverage tools not just in the python development stack, such
as CobraPy but also other strain design methods from the likes of Matlab and OptKnock. This is achieved through
a command line api that allows the export of files in to a variety of formats. This ensures that good standards
can be followed and maintained.

* **Reusability of previous designs**
The constraints, reactions, genes and metabolites for different designs can be a headache to manage. Generally, a
base strain will exist and users will modify this over a long period of time. Likewise, designs the exploit existing
hetrologous pathways or optimisations can be reused through an inherited design approach.

* **Testability of models**
The validity of a model is a difficult aspect to measure. Constant manual curation in order to match experimental
data requires users to check conditions. For this reason a testing framework is adopted allowing models to maintain
conditions of validation. By default added growth constraints and designs can be tested. Users can also write tests
in python and JSON to ensure that essential pathways are maintained and validation against experimental data is met.

* **Sharability**
The design of the project uses flat files rather than database systems. Whilst this looses some power it ensures
that any models developed can be shared easily through distributed source control software like Git
and mercurial. Similarly, in the future the project aims to allow models to be distributed via Docker containers
allowing controlled environments to improve collaboration where users require more than just a model to perform
complex analysis.


## Installation

To install the latest release from pip:

    pip install gsmodutils

To install this software clone the git repository and type:

    pip install -r requriements.txt
    python setup.py install
    
To run the tests for this project, install pytest and, from the project root directory simply run

    pytest
    
gsmodutils is fully compatible with python 2.7+ and python 3.5+.
(TODO) Software has been tested on linux (Ubuntut, manjaro/arch), windows and MacOSX. 

### Install and using the docker image

The simplest method of installation is probably with docker. 
Follow the install instructions for docker found at docker.io clone the git repository found here and then run

    docker build . -t gsmoduitls

This will create a gsmodutils docker image that can be resused for prjects.

## Usage
Please read the user guide in the docs!

## See also

This project would be nothing without other great open source software projects.
In particular, we would like to draw attention to ```cameo``` and ```cobrapy```.
These projects offer a wide array of functionality for FBA and other constraints based
analysis within the python open source stack.


## Contributors
James Gilbert  University of Nottingham - main software developer.
Nicole Pearcy - Testing, ideas and knowledge of genome scale models.

If you would like to collaborate, please get in touch!
