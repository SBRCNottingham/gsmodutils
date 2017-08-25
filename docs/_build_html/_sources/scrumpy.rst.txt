ScrumPy
=======
The ScrumPy modelling software is developed at Oxford Brookes univeristy by the cell systems modelling group:

http://mudshark.brookes.ac.uk/ScrumPy
http://mudshark.brookes.ac.uk/

This utility is mainly based around the ``scrumpy_to_cobra`` cli utility

Example usage
-------------

.. code-block:: guess

    $ scrumpy_to_cobra --model SCRUMPY_FILE.spy --output OUTPUT_FILE.json

As scrumpy spy files do not include constraints for models, the following options are probably required to get
a working model

.. code-block:: guess

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


Code docs
---------
.. automodule:: gsmodutils.utils.scrumpy
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance: