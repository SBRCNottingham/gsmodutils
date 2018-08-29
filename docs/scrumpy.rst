ScrumPy
=======
The ScrumPy modelling software is developed at Oxford Brookes univeristy by the cell systems modelling group:

http://mudshark.brookes.ac.uk/ScrumPy

http://mudshark.brookes.ac.uk/

This documentation is for the ``scrumpy_to_cobra`` utility and associated functions.
Gsmodutils is capable of converting ScrumPy structural models to cobrapy objects.
However, it should be noted that additional constraints on reactions are not specified within the ScrumPy modelling format.
As a consequence, these will have to be specified manually (or through supported json formats).

Example usage
-------------

.. code-block:: bash

    $ scrumpy_to_cobra --model SCRUMPY_FILE.spy --output OUTPUT_FILE.json


As scrumpy spy files do not include constraints for models, the following options are probably required to get
a working model


.. code-block:: text

    --media a json file for growth media

    --atpase_reaction

    --atpase_flux

    --objective_reaction Objective to maximise (multiple objectives currently not set)

    --objective_direction

Alternatively, use the python interface to load a model and set the constraints with the cobrapy interface

.. code-block:: python

    from gsmodutils.utils.scrumpy import load_scrumpy_model
    cobra_mdl = load_scrumpy_model('model.spy')
    cobra_mdl.objective = cobra_mdl.reactions.Biomass
    cobra.mdl.reactions.ATPase.lower_bound = -8.0
    cobra.mdl.reactions.ATPase.upper_bound = -8.0


Scrumpy formatted strings can also be loaded in to gsmodutils models on the fly.
For example, after a gsmodutils project model is loaded:

.. code-block:: python

    from gsmodutils import GSMProject
    project = GSMProject()
    model = project.model

    spy_reactions = """
    External(PROTON_i, "WATER")

    NADH_DH_ubi:
        "NADH" + "UBIQUINONE-8" + 4 PROTON_i -> "UBIQUINOL-8" + 3 PROTON_p + "NAD"
        ~

    NADH_DH_meno:
        "NADH" + "Menaquinones" + 4 PROTON_i -> "Menaquinols" + 3 PROTON_p + "NAD"
        ~
    """
    model.add_scrumpy_reactions(spy_reactions)

A further usage is to load cobra models directly from scrumpy strings:

.. code-block:: python

    from gsmodutils.utils.scrumpy import load_scrumpy_model
    spy_reactions = """
    Structural()
    External(PROTON_i, "WATER")

    NADH_DH_ubi:
        "NADH" + "UBIQUINONE-8" + 4 PROTON_i -> "UBIQUINOL-8" + 3 PROTON_p + "NAD"
        ~

    NADH_DH_meno:
        "NADH" + "Menaquinones" + 4 PROTON_i -> "Menaquinols" + 3 PROTON_p + "NAD"
        ~
    """
    model = load_scrumpy_model(spy_reactions)

Naturally, any constraints additional to reaction directionality (such as uptake) will have to be specified manually.

Code docs
---------
.. automodule:: gsmodutils.utils.scrumpy
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance: