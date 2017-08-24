Creating Designs
================
gsmodutils aims to create convenient interaction with strain designs through use of ``designs``.
A design is any complex set of constrains that adds or removes reactions or changes the constraints of a model in any
way.

The storage of designs within a project is a collection of flat json objects in the designs folder.

The reason for flat files over a database is to allow easy interoperability with revision control software.

Designs can inherit from one another and should, essentially, be considered as the difference between two models.

Where differences are large it may be desirable to have a separate model in the project.

However, for many cases a single model with different strain designs matching real strains stored in a culture collection is enough.

For example, this can be for the addition of hetrologous pathways, or kockouts that are commonly used to improve the
productions of desired chemicals.

Adding designs
--------------

There are many cases in which an organism maybe modified in complex
ways. In this example we apply some of the work from [1] and add the
reactions for the Calvin-Benson (CBB) cycle to the ecoli model. This
allows the fixation of CO2 as an inorganic carbon source.

To do this, we need to add two enzymatic reactions to the model
Phosphoribulokinase and Rubisco.

.. code:: ipython3

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





.. raw:: html


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




.. code:: ipython3

    # now rubisco
    rubisco




.. raw:: html


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




.. code:: ipython3

    # Removed pfkA, pfkB and zwf
    model.genes.get_by_id("b3916").knock_out()
    model.genes.get_by_id("b1723").knock_out()
    model.genes.get_by_id("b1852").knock_out()

Now we have added the reactions, we would probably want to make sure
they work. To do this we need to change the medium.

.. code:: ipython3

    from cameo.core.utils import medium, load_medium

    model.reactions.EX_glc__D_e.lower_bound = -10.0
    model.reactions.EX_nh4_e.lower_bound = -1000.0

    model.optimize().f




.. parsed-literal::

    0.9686322977222491



.. code:: ipython3

    design = project.save_design(model, 'cbb_cycle', 'calvin cycle',
                        description='Reactions necissary for the calvin cycle in ecoli', overwrite=True)

Inherited designs
~~~~~~~~~~~~~~~~~

Now we would like to use the design for production of xylose To do this
we will create a child design so we can reuse the calvin cycle without
making it part of the wild type ecoli core model.

First, we want to start from the parent calvin cycle design as a base.

.. code:: ipython3

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




.. raw:: html


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




.. code:: ipython3

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




.. raw:: html


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




.. code:: ipython3

    model.add_boundary(mev__R, type='sink') # add somewhere for mevalonate to go

    design = project.save_design(model, 'mevalonate_cbb', 'mevalonate production', parent='cbb_cycle',
                        description='Reactions for the production of mevalonate', overwrite=True)

.. code:: ipython3

    des = project.load_design('mevalonate_cbb')
    des




.. raw:: html


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



Accessing designs as models
---------------------------

By default a design can be accessed as a model with

::

    project.load_design(<design_id>)

This loads the design as a cobra model object.

Using the get\_design method allows access to the strain design object.

::

    project.get_design(<design_id>)

This can also be loaded as an isolated pathway cobra model (though FBA
cannot be performed on this object).

.. code:: ipython3

    from gsmodutils import GSMProject
    project = GSMProject('example_project')
    des = project.get_design('mevalonate_cbb')
    des.as_pathway_model()




.. raw:: html


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



.. code:: ipython3

    des = project.get_design('cbb_cycle')
    des.as_pathway_model()




.. raw:: html


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



Exporting and importing designs and conditions
==============================================

There are many cases where a particular external piece of software
outside the cobrapy stack will be needed for strain design. For this
reason the gsmodutils import and export commands aim to allow
interoperability with other tool sets.

The objective is to allow users to add or update designs to the project
through the command line alone as well as exporting models with the
additional constraints that are applied for import in to other tools.
Cobrapy makes it easy to work with matlab, sbml, json and yaml
constraints based models.

Viewing a project's designs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To view the designs and conditions stored in a project use the ``info``
command. For the example project it should look something like:

::

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

Exporting a design
~~~~~~~~~~~~~~~~~~

To export to matlab, sbml, json or yaml formats use
``gsmodutils export``:

::

    gsmodutils export <output format> <output filepath> --model_id <model id> --conditions <conditions_id> --design <design_id>

For example:

::

    gsmodutils export mat mevalonate_analysis.mat --design mevalonate_cbb

A note on conflicting constraints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When flags for models, designs and conditions are all set the load order
of constrains is as follows: \* Load model \* Set conditions \* Load
design

This means that if there is a conflict betweeen the constraints set in a
conditions file and the design file (i.e. the same transporter may be
switched on an off at the same time) the constraint added in the design
file takes precidence and is applied to the model.

Importing a new design
~~~~~~~~~~~~~~~~~~~~~~

To import a new design use the ``dimport`` command:

::

    gsmodutils dimport <path_to_model> <new_id> --base_model <base_model_id> --parent <parent_design_id>

The base\_model flag is optional, if it is unset the default project
modell will be used for the diff.

Before adding a new design it may be desirable to check the diff summary
using:

::

    gsmodutils diff <path_to_model> --base_model <base_model_id> --parent <parent_design_id>

This command shows a summary of the changes the design makes. Using the
flag ``--no-names`` will create a summary that only lists the number of
reactions and metabolites modified or added. By default, all changed
reactions will be listed by name (though the exact changes are not
visible).

Using ``--output`` allows the diff to be saved as a json file. This can
then be imported directly as a design with ``dimport`` using the
``--from-diff`` flag.

Modifying an existing design with another tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than saving a new design, we would like to simply overwrite the
existing design. This can be done easily. **However, it is strongly
reccommended that you use version control software (such as git or
mercurial) to ensure that changes to existing designs are tracked.**

Do this with the command

::

    gsmodutils dimport <path_to_updated_model> <design_id> --overwrite


StrainDesign class
------------------

.. automodule:: gsmodutils.design
:members:
        :undoc-members:
            :inherited-members:
            :show-inheritance: