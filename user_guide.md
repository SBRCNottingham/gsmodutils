
# Creating projects and running tests


## Project creation

The first step for the use of gsmodutils for assitance with managing curated genome scale models is the creation of the necissary project files. This is a configuration that only needs to be done once before models and designs can be added.

In python this can be achived as follows


```python
from gsmodutils import GSMProject
from cameo import models
import cobra

model = models.bigg.e_coli_core
```


```python
# Note, running more than once will throw an error. Projects can't be created in the folder more than once.
project = GSMProject.create_project(
    models=[models.bigg.iJO1366],
    description='Example ecoli core model',
    author='A user',
    author_email='A.user@example.com',
    project_path='example_project'
)
```

Alternatively, we reccomend the usage of the cli interface with the following command. This will prompt you for the necissary descriptions.
gsmodutils create_project ./example_project <path to ecoli_model.json/sbml/mat>
The project folder "ecoli_core_model" should now be created containing the barebones of a new project directory. The model file will be copied. Alternatively a project file can be created in a directory with an already existing model and other files. In th

## Adding some growth conditions

In many cases it is desirable to compare models configured with different growth conditions. In this simplistic example we show how conditions can be adjusted by switching the growth media from glucose to fructose. This setting can then be saved and reloaded at a later time.


```python
from gsmodutils import GSMProject
# Load existing project
project = GSMProject('example_project')
model = project.model

# Switching off glucose uptake
model.reactions.EX_glc__D_e.lower_bound = 0
# switching on Xylose uptake
model.reactions.EX_fru_e.lower_bound = -10
# Check it works
s = model.optimize()
project.save_conditions(model, 'fructose_growth')

```


```python
# loading the conditions back into a different model
fructose_m = project.load_conditions('fructose_growth')

# fructose should be in the medium
# Glucose should not be present
assert "EX_fru_e" in fructose_m.medium
assert "EX_glc__D_e" not in fructose_m.medium

assert fructose_m.medium["EX_fru_e"] == 10

```

## Adding designs

There are many cases in which an organism maybe modified in complex ways. In this example we apply some of the work from  [1] and add the reactions for the Calvin-Benson (CBB) cycle to the ecoli model. This allows the fixation of CO2 as an inorganic carbon source.

To do this, we need to add two enzymatic reactions to the model Phosphoribulokinase and Rubisco.



```python
from gsmodutils import GSMProject
import cobra

# Load existing project
project = GSMProject('example_project')
# Load the default model we want to add
model = project.load_model()

# Phosphoribulokinase reaction
stoich = dict(
    atp_c=-1.0,
    ru5p__D_c=-1.0,
    adp_c=1.0,
    h_c=1.0,
    rb15bp_c=1.0,
)


rb15bp = cobra.Metabolite(id='rb15bp_c', name='D-Ribulose 1,5-bisphosphate', formula='C5H8O11P2')
model.add_metabolites(rb15bp)

pruk = cobra.Reaction(id="PRUK", name="Phosphoribulokinase reaction", lower_bound=-1000, upper_bound=1000)
model.add_reaction(pruk)
pruk.add_metabolites(stoich)


# Rubisco reaction (Ribulose-bisphosphate carboxylase)
stoich = {
    "3pg_c":2.0,
    "rb15bp_c":-1.0,
    "co2_c":-1.0,
    "h2o_c":-1.0,
    "h_c":2.0
}


rubisco = cobra.Reaction(id="RBPC", lower_bound=0, upper_bound=1000.0, name="Ribulose-bisphosphate carboxylase")

model.add_reaction(rubisco)
rubisco.add_metabolites(stoich)

#show the reactions
pruk

```





        <table>
            <tr>
                <td><strong>Reaction identifier</strong></td><td>PRUK</td>
            </tr><tr>
                <td><strong>Name</strong></td><td>Phosphoribulokinase reaction</td>
            </tr><tr>
                <td><strong>Memory address</strong></td>
                <td>0x07f2b1b81cad0</td>
            </tr><tr>
                <td><strong>Stoichiometry</strong></td>
                <td>
                    <p style='text-align:right'>atp_c + ru5p__D_c <=> adp_c + h_c + rb15bp_c</p>
                    <p style='text-align:right'>ATP + D-Ribulose 5-phosphate <=> ADP + H+ + D-Ribulose 1,5-bisphosphate</p>
                </td>
            </tr><tr>
                <td><strong>GPR</strong></td><td></td>
            </tr><tr>
                <td><strong>Lower bound</strong></td><td>-1000</td>
            </tr><tr>
                <td><strong>Upper bound</strong></td><td>1000</td>
            </tr>
        </table>
        




```python
# now rubisco
rubisco
```





        <table>
            <tr>
                <td><strong>Reaction identifier</strong></td><td>RBPC</td>
            </tr><tr>
                <td><strong>Name</strong></td><td>Ribulose-bisphosphate carboxylase</td>
            </tr><tr>
                <td><strong>Memory address</strong></td>
                <td>0x07f2b1b49fa50</td>
            </tr><tr>
                <td><strong>Stoichiometry</strong></td>
                <td>
                    <p style='text-align:right'>co2_c + h2o_c + rb15bp_c --> 2.0 3pg_c + 2.0 h_c</p>
                    <p style='text-align:right'>CO2 + H2O + D-Ribulose 1,5-bisphosphate --> 2.0 3-Phospho-D-glycerate + 2.0 H+</p>
                </td>
            </tr><tr>
                <td><strong>GPR</strong></td><td></td>
            </tr><tr>
                <td><strong>Lower bound</strong></td><td>0</td>
            </tr><tr>
                <td><strong>Upper bound</strong></td><td>1000.0</td>
            </tr>
        </table>
        




```python
# Removed pfkA, pfkB and zwf
model.genes.get_by_id("b3916").knock_out()
model.genes.get_by_id("b1723").knock_out()
model.genes.get_by_id("b1852").knock_out()
```

Now we have added the reactions, we would probably want to make sure they work. To do this we need to change the medium.


```python
from cameo.core.utils import medium, load_medium

model.reactions.EX_glc__D_e.lower_bound = -10.0
model.reactions.EX_nh4_e.lower_bound = -1000.0

model.optimize().f
```




    0.9686322977222491




```python
design = project.save_design(model, 'cbb_cycle', 'calvin cycle', 
                    description='Reactions necissary for the calvin cycle in ecoli', overwrite=True)
```

### Inherited designs

Now we would like to use the design for production of xylose
To do this we will create a child design so we can reuse the calvin cycle without making it part of the wild type ecoli core model. 

First, we want to start from the parent calvin cycle design as a base.


```python
project = GSMProject('example_project')
# Start from the design as a base model
model = project.load_design('cbb_cycle')
reaction = cobra.Reaction(id="HMGCOASi", name="Hydroxymethylglutaryl CoA synthase")

aacoa = cobra.Metabolite(id="aacoa_c", charge=-4, formula="C25H36N7O18P3S", name="Acetoacetyl-CoA")
hmgcoa = cobra.Metabolite(id="hmgcoa_c", charge=-5, formula="C27H40N7O20P3S", name="Hydroxymethylglutaryl CoA")


model.add_metabolites([aacoa, hmgcoa])

stoich = dict(
    aacoa_c=-1.0, 
    accoa_c=-1.0,
    coa_c=1.0,
    h_c=1.0,
    h2o_c=-1.0,
    hmgcoa_c=1.0,
)


model.add_reaction(reaction)
reaction.add_metabolites(stoich)
reaction.lower_bound = -1000.0
reaction.upper_bound = 1000.0

reaction
```





        <table>
            <tr>
                <td><strong>Reaction identifier</strong></td><td>HMGCOASi</td>
            </tr><tr>
                <td><strong>Name</strong></td><td>Hydroxymethylglutaryl CoA synthase</td>
            </tr><tr>
                <td><strong>Memory address</strong></td>
                <td>0x07f2b18b7d790</td>
            </tr><tr>
                <td><strong>Stoichiometry</strong></td>
                <td>
                    <p style='text-align:right'>aacoa_c + accoa_c + h2o_c <=> coa_c + h_c + hmgcoa_c</p>
                    <p style='text-align:right'>Acetoacetyl-CoA + Acetyl-CoA + H2O <=> Coenzyme A + H+ + Hydroxymethylglutaryl CoA</p>
                </td>
            </tr><tr>
                <td><strong>GPR</strong></td><td></td>
            </tr><tr>
                <td><strong>Lower bound</strong></td><td>-1000.0</td>
            </tr><tr>
                <td><strong>Upper bound</strong></td><td>1000.0</td>
            </tr>
        </table>
        




```python
mev__R = cobra.Metabolite(id="mev__R_c", name="R Mevalonate", charge=-1, formula="C6H11O4")
model.add_metabolites([mev__R])

reaction = cobra.Reaction(id="HMGCOAR", name="Hydroxymethylglutaryl CoA reductase")
reaction.lower_bound = -1000.0
reaction.upper_bound = 1000.0

stoich = dict(
    coa_c=-1.0,
    h_c=2.0,
    nadp_c=-2.0,
    nadph_c=2.0,
    hmgcoa_c=1.0,
    mev__R_c=-1.0
)

model.add_reaction(reaction)

reaction.add_metabolites(stoich)
reaction
```





        <table>
            <tr>
                <td><strong>Reaction identifier</strong></td><td>HMGCOAR</td>
            </tr><tr>
                <td><strong>Name</strong></td><td>Hydroxymethylglutaryl CoA reductase</td>
            </tr><tr>
                <td><strong>Memory address</strong></td>
                <td>0x07f2b19fc3290</td>
            </tr><tr>
                <td><strong>Stoichiometry</strong></td>
                <td>
                    <p style='text-align:right'>coa_c + mev__R_c + 2.0 nadp_c <=> 2.0 h_c + hmgcoa_c + 2.0 nadph_c</p>
                    <p style='text-align:right'>Coenzyme A + R Mevalonate + 2.0 Nicotinamide adenine dinucleotide phosphate <=> 2.0 H+ + Hydroxymethylglutaryl CoA + 2.0 Nicotinamide adenine dinucleotide phosphate - reduced</p>
                </td>
            </tr><tr>
                <td><strong>GPR</strong></td><td></td>
            </tr><tr>
                <td><strong>Lower bound</strong></td><td>-1000.0</td>
            </tr><tr>
                <td><strong>Upper bound</strong></td><td>1000.0</td>
            </tr>
        </table>
        




```python
model.add_boundary(mev__R, type='sink') # add somewhere for mevalonate to go

design = project.save_design(model, 'mevalonate_cbb', 'mevalonate production', parent='cbb_cycle',
                    description='Reactions for the production of mevalonate', overwrite=True)
```


```python
des = project.load_design('mevalonate_cbb')
des
```





        <table>
            <tr>
                <td><strong>Name</strong></td>
                <td>iJO1366:ds_cbb_cycle:ds_cbb_cycle:ds_mevalonate_cbb</td>
            </tr><tr>
                <td><strong>Memory address</strong></td>
                <td>0x07f2b1856a490</td>
            </tr><tr>
                <td><strong>Number of metabolites</strong></td>
                <td>1808</td>
            </tr><tr>
                <td><strong>Number of reactions</strong></td>
                <td>2588</td>
            </tr><tr>
                <td><strong>Objective expression</strong></td>
                <td>-1.0*BIOMASS_Ec_iJO1366_core_53p95M_reverse_5c8b1 + 1.0*BIOMASS_Ec_iJO1366_core_53p95M</td>
            </tr><tr>
                <td><strong>Compartments</strong></td>
                <td>periplasm, cytosol, extracellular space</td>
            </tr>
          </table>



## Accessing designs as models

By default a design can be accessed as a model with
```
project.load_design(<design_id>)
``` 
This loads the design as a cobra model object.

Using the get_design method allows access to the strain design object.
```
project.get_design(<design_id>)
```
This can also be loaded as an isolated pathway cobra model (though FBA cannot be performed on this object).


```python
from gsmodutils import GSMProject
project = GSMProject('example_project')
des = project.get_design('mevalonate_cbb')
des.as_pathway_model()
```





        <table>
            <tr>
                <td><strong>Name</strong></td>
                <td>:ds_cbb_cycle:ds_mevalonate_cbb</td>
            </tr><tr>
                <td><strong>Memory address</strong></td>
                <td>0x07fddd6c806d0</td>
            </tr><tr>
                <td><strong>Number of metabolites</strong></td>
                <td>23</td>
            </tr><tr>
                <td><strong>Number of reactions</strong></td>
                <td>9</td>
            </tr><tr>
                <td><strong>Objective expression</strong></td>
                <td>0</td>
            </tr><tr>
                <td><strong>Compartments</strong></td>
                <td></td>
            </tr>
          </table>




```python
des = project.get_design('cbb_cycle')
des.as_pathway_model()
```





        <table>
            <tr>
                <td><strong>Name</strong></td>
                <td>:ds_cbb_cycle</td>
            </tr><tr>
                <td><strong>Memory address</strong></td>
                <td>0x07fde0f3c0790</td>
            </tr><tr>
                <td><strong>Number of metabolites</strong></td>
                <td>18</td>
            </tr><tr>
                <td><strong>Number of reactions</strong></td>
                <td>6</td>
            </tr><tr>
                <td><strong>Objective expression</strong></td>
                <td>0</td>
            </tr><tr>
                <td><strong>Compartments</strong></td>
                <td></td>
            </tr>
          </table>



# Exporting and importing designs and conditions

There are many cases where a particular external piece of software outside the cobrapy stack will be needed for strain design. For this reason the gsmodutils import and export commands aim to allow interoperability with other tool sets.

The objective is to allow users to add or update designs to the project through the command line alone as well as exporting models with the additional constraints that are applied for import in to other tools. Cobrapy makes it easy to work with matlab, sbml, json and yaml constraints based models.

### Viewing a project's designs

To view the designs and conditions stored in a project use the ```info``` command.
For the example project it should look something like:

```
--------------------------------------------------------------------------------------------------
Project description - Example ecoli core model
Author(s): - A user
Author email - A.user@example.com
Designs directory - designs
Tests directory - tests   
    
Models:
        * iJO1366.json
                 iJO1366
                 
Designs:
        * mevalonate_cbb
                 mevalonate production
                 Reactions for the production of mevalonate
                 Parent: cbb_cycle
        * cbb_cycle
                 calvin cycle
                 Reactions necissary for the calvin cycle in ecoli
Conditions:
        * fructose_growth
--------------------------------------------------------------------------------------------------

```

### Exporting a design
To export to matlab, sbml, json or yaml formats use ```gsmodutils export```:

```
gsmodutils export <output format> <output filepath> --model_id <model id> --conditions <conditions_id> --design <design_id>
```

For example:

```
gsmodutils export mat mevalonate_analysis.mat --design mevalonate_cbb
```

#### A note on conflicting constraints
When flags for models, designs and conditions are all set the load order of constrains is as follows:
* Load model
* Set conditions
* Load design

This means that if there is a conflict betweeen the constraints set in a conditions file and the design file (i.e. the same transporter may be switched on an off at the same time) the constraint added in the design file takes precidence and is applied to the model.

### Importing a new design

To import a new design use the ``dimport`` command: 
```
gsmodutils dimport <path_to_model> <new_id> --base_model <base_model_id> --parent <parent_design_id>
```
The base_model flag is optional, if it is unset the default project modell will be used for the diff.

Before adding a new design it may be desirable to check the diff summary using:

```
gsmodutils diff <path_to_model> --base_model <base_model_id> --parent <parent_design_id>
```
This command shows a summary of the changes the design makes. Using the flag ``--no-names`` will create a summary that only lists the number of reactions and metabolites modified or added. By default, all changed reactions will be listed by name (though the exact changes are not visible).

Using ``--output`` allows the diff to be saved as a json file. This can then be imported directly as a design with ``dimport`` using the ``--from-diff`` flag.

### Modifying an existing design with another tool

Rather than saving a new design, we would like to simply overwrite the existing design. This can be done easily. **However, it is strongly reccommended that you use version control software (such as git or mercurial) to ensure that changes to existing designs are tracked.**

Do this with the command
```
gsmodutils dimport <path_to_updated_model> <design_id> --overwrite
```


```python

```

# Tests

## Running the default tests
A test report can be generated by the tester. This is a command line utility which, by default, loads each model, set of conditions and design and performs the FBA simulations. This ensures that any changes to the project files maintain designs, models and conditions.
gsmodutils test
The output from the terminal should look something like this:
------------------------- gsmodutils test results -------------------------
Running tests: ....
Default project file tests (models, designs, conditions):
Counted 4 test assertions with 0 failures
Project file completed all tests without error
    --model_e_coli_core.json

    --design_mevalonate_calvin

    --design_mevalonate_cbb

    --design_cbb_cycle

Ran 4 test assertions with a total of 0 errors (100.0% success)

## Adding custom tests

Whilst the default tests provided by the tool are a useful way of ensuring that the project files remain valid after manual curation they do not have the capability to match all design goals. These design goals will be based on a data driven approach to genome scale model development and often require a more fundamental understanding of how an organism functions.

For this reason we give an example here of the TCA cycle in E coli. In our case this is a pathway that should be conserved and used in all FBA cases. If a modification were to break this (without being a specific engineering goal) the model's validity comes in to question.

## Writing python test cases
For many use cases, it may require the use of more complex functionality. For this reason, gsmodutils allows users to write fully featured python test cases. This means that any code written in python can be used and assertion statments can be written and included in the test reports.


```python

```

## Sharing projects with docker

This section describes how to share a gsmodutils project inside a docker container. The objective is to have code for testing models, data for their validation and the framework for running models written in a "write once run anywhere" fashion. Ideally, even if a platform for running a model is considerably out of date it should produce the same results on new software. Unfortunately this isn't always the case. Packaging a constraints based model, with associated software, within the same working environment ensures that the results should be reproducable, providing other users can install docker containers.

To install docker on your system please consult the documentation at docs.docker.com

### Creating a docker container

To create a new docker container (with the latest gsmodutils setup scripts,
use the docker utility.
```
gsmodutils docker --overwrite
```
This will overwrite any existing dockerfiles.
Now to create a docker container use the build command

```
docker build -t="example_project" <path_to_gsmodutils_project>
```

This will install the required python components for ``gsmodutils``.

### Running a docker container

``gsmodutils`` just provides the basic dockerfile. In future iterations this may be changes.
To use code inside a docker image, run the command

```
docker run -it <command>
```

For example, to load an ``ipython`` shell run:

```
docker run -it example_project ipython
```

You might wish to get the project info:
```
ocker run -it example_project gsmodutils info
--------------------------------------------------------------------------------------------------
Project description - Example ecoli core model
Author(s): - A user
Author email - A.user@example.com
Designs directory - designs
Tests directory - tests

Models:
 * iJO1366.json
   iJO1366

Designs:
 * cbb_cycle
   calvin cycle
   Reactions necissary for the calvin cycle in ecoli
 * mevalonate_cbb
   mevalonate production
   Reactions for the production of mevalonate
   Parent: cbb_cycle
Conditions:
 * fructose_growth
--------------------------------------------------------------------------------------------------

```

Another example might be to run the ```gsmodutils test``` inside this portable environement:

```
docker run -it example_project gsmodutils test
------------------------- gsmodutils test results -------------------------
Running tests: ....
Default project file tests (models, designs, conditions):
Counted 4 test assertions with 0 failures
Project file completed all tests without error
    --model_iJO1366.json

    --conditions_iJO1366.json:model_fructose_growth

    --design_cbb_cycle

    --design_mevalonate_cbb

Ran 4 test assertions with a total of 0 errors (100.0% success)
```



### Sharing and loading gsmodutils docker images

To share a project with users, first build it following the steps above.
When the project is built use the command:
```
docker save example_project -o example_project.tar
```

This saves the sharable docker container.
When this tarball is transferred to another user, they can load the image with the command:

```
docker load -i example_project.tar
```

The imported image will then allow the above commands to run with the same environmental settings.
This should allow you to share your models in a way that allows results to be replicated without worrying about the software.

### Refrences

[1] Antonovsky, N., Gleizer, S., Noor, E., Zohar, Y., Herz, E., Barenholz, U., Zelcbuch, L., Amram, S., Wides, A., Tepper, N. and Davidi, D., 2016. Sugar synthesis from CO 2 in Escherichia coli. Cell, 166(1), pp.115-125.

[2] Ebrahim, Ali, Joshua A. Lerman, Bernhard O. Palsson, and Daniel R. Hyduke. "COBRApy: COnstraints-based reconstruction and analysis for python." BMC systems biology 7, no. 1 (2013): 74.

[3] Cardoso, Joao, Kristian Jensen, Christian Lieven, Anne Sofie Laerke Hansen, Svetlana Galkina, Moritz Emanuel Beber, Emre Ozdemir, Markus Herrgard, Henning Redestig, and Nikolaus Sonnenschein. "Cameo: A Python Library for Computer Aided Metabolic Engineering and Optimization of Cell Factories." bioRxiv (2017): 147199.



```python

```
