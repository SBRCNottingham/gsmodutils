Projects
======================================
Projects are at the heart of gsmodutils.
Essentially, a project is a directory that contains all the models, designs, conditions and other gsmodutils tools
such as Docker files.

Creating projects
-----------------
Project creation is best done with the command line utility.
This provides a step by step guide for project creation.

.. code-block:: guess

    $ gsmodutils create_project PROJECT_PATH MODEL_PATH


Alternatively, this can be done in python using the GSMProject class.

.. code-block:: python

    from gsmodutils import GSMProject
    from cameo import models

    model = models.bigg.e_coli_core

    # Note, running more than once will throw an error.
    # Projects can't be created in the folder more than once.
    project = GSMProject.create_project(
        models=[model],
        description='Example ecoli core model',
        author='A user',
        author_email='A.user@example.com',
        project_path='example_project'
    )

Using the cli lets have a look inside the newly created project:

.. code-block:: guess

    $ gsmodutils create_project ./example_project e_coli_core.json
    ...
    $ cd example_project
    $ gsmodutils info
    --------------------------------------------------------------------------------------------------
    Project description - Example ecoli core model
    Author(s): - A user
    Author email - A.user@example.com
    Designs directory - designs
    Tests directory - tests

    Models:
            * e_coli_core.json
                     e_coli_core
    --------------------------------------------------------------------------------------------------


This will also allow access to a project object that can be used to access gsmodutils features, such as accessing models

.. code-block:: python

    from gsmodutils import GSMProject
    project = GSMProject('example_project')
    # load the default model
    model = project.load_model()


It is now recomended that you use source control, such as ``git`` or ``mercurial``, create a repository and add the
project to it to track all changes to models that are made over the course of the project.

Adding conditions
-----------------
In many cases it is desirable to compare models configured with different growth conditions.
In this simplistic example we show how conditions can be adjusted by switching the growth media from glucose to
fructose.
This setting can then be saved and reloaded at a later time.

.. code-block:: python

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


Loading them back should now be straightforward:

.. code-block:: python

    # loading the conditions back into a different model
    fructose_m = project.load_conditions('fructose_growth')

    # These will raise assertion errors if this hasn't worked
    # fructose should be in the medium
    # Glucose should not be present
    assert "EX_fru_e" in fructose_m.medium
    assert "EX_glc__D_e" not in fructose_m.medium
    assert fructose_m.medium["EX_fru_e"] == 10



GSMProject class
----------------

.. automodule:: gsmodutils.project
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance:

