MetaCyc
=======

This module provides a set of utilities for handling metacyc databases.
This code does not provide access to the metacyc/biocyc databases and is simply a parser.
For access to data consult metacyc for the acquisition of a valid licence.

Example usage
-------------
The intended uscase for this code is to allow the addition of pathways to models that use metacyc identifiers.
The example bellow adds an enzyme to a model using EC identifiers.

.. code-block:: python

    from gsmodutils import GSMProject
    from gsmodutils import metacyc
    db = metacyc.parse_db('/path/to/metacyc/dat/files')
    project = GSMProject()

    model = project.load_model()

    metacyc.add_pathway(model, ["EC-1.2.1.10"])


Code docs
----------
.. automodule:: gsmodutils.utils.metacyc
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance: