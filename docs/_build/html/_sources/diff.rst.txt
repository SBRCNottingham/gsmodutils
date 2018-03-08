Model diffs
===========
When making changes to a model within ``gsmodutils`` the ``gsmodutils.GSModuitlsModel`` instances (which is subclass
of ``cobra.Model``) allows you to track the differences between the in memory model and the model or design saved
on disk.
For example:

.. code-block:: python

    import gsmodutils
    project = gsmodutils.GSMProject()
    model = project.load_model()

    model.remove_reactions([model.reactions.RXN_01])

    diff = model.diff()
    diff


Diff is gsmodutils.model_diff.ModelDiff object which is just a subclass of a python dictionary.
If working within an jupyter notebook diff will display the model changes in HTML.

If working outside of as gsmodutils project with cobra models use:

.. code-block:: python

    from gsmodutils.model_diff import ModelDiff
    diff = ModelDiff.model_diff(model_a, model_b)
    diff

ModelDiff class
----------------

.. automodule:: gsmodutils.model_diff
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance: