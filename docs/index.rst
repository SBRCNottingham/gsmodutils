.. gsmodutils documentation master file, created by sphinx-quickstart on Thu Aug 24 10:33:30 2017.

gsmodutils - genome scale model management utilities
===========================================================

``gsmodutils`` is a set of utilities that aim to improve the management of large constraints based models geared
towards strain design and analysis.
Think of it as a friendly framework for developing genome scale models.

The core aim of this software is to make genome scale models, and their applications, reusable in future projects.
This is inspired by the notion of *test driven development*.

Changes to models are tracked and pre-written test cases ensure that changes don't break already working components.
In addition, by following good practices, well documented genome scale models can be an accompaniment to papers,
a core goal of ``gsmodutils`` is to allow users to share their projects in self contained ``docker`` images.

**Note that this software is under heavy development and much of this may change. Please check back here**
**or at the git hub repository for updates.**

**It is currently recommended that you install gsmodutils in a** ``virtualenv`` **environment**.


The most important thing, though, is to not have a model file for every small set of constraints that are added to a
model.

E.g. having a directory structure such as this isn't good for anyone. You might add new curation to the base model,
or a knockout might exist in one model but not another.

.. code-block:: guess

    $ ls my_project
    ecoli_base_model.sbml
    ecoli_model_with_xylose_growth.sbml
    ecoli_model_with_fructose_growth.sbml
    ecoli_model_with_succinate_production.sbml
    ecoli_model_with_succinate_production_on_xylose.sbml
    ...
    ecoli_model_with_succinate_production_on_xylose_JUNE_2015_PUBLISHED_VERSION.sbml


Instead ``gsmodutils`` takes the philopsophy that we should be storing the changes (ie. *diffs* or *deltas*) between
different versions of models.
For this reason, gsmodutils uses simple utilities that let you load model ``conditions`` and ``designs`` in python:

.. code-block:: python

    from gsmodutils import GSMProject
    project = GSMProject()
    # Just load a model
    model = project.load_model()
    # Just load some conditions
    xylose_growth = project.load_conditions('xylose_growth')
    # Load a strain design
    succ_prod = project.load_design('succinate_production')
    # or load it growing on a different substrate
    succ_prod_xyl = project.load_design('succinate_production', conditions='xylose_growth')


Or you can export them through the convenient command line utility to export models for use in other tools outside the
cobrapy world.

.. code-block:: guess

    $ gsmodutils export matlab succ_production.m --design succinate_production --conditions xylose_growth


Installation
------------
To install, the simplest method is to use pip

.. code-block:: guess

    $ pip install gsmodutils

Alternatively, from sources use

.. code-block:: guess

    $ pip install -r requirements.txt
    $ python setup.py install

User guides
------------
Project creation is the first step. This can be done as simply

.. code-block:: guess

    $ gsmodutils create_project PROJECT_PATH MODEL_PATH

This will give a step by step guide.

.. toctree::
    project
    designs
    cli
    tests
    docker
    :maxdepth: 2
    :caption: User Guide:


Other utilities
---------------
gsmodutils also includes utilities for genome scale model managament.
Particularly the parsing of ScrumPy files (constraints based models developed at oxford brookes university).

.. toctree::
    metacyc
    scrumpy
    :maxdepth: 2
    :caption: Utilities:

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


References
~~~~~~~~~~
[1] Antonovsky, N., Gleizer, S., Noor, E., Zohar, Y., Herz, E.,
Barenholz, U., Zelcbuch, L., Amram, S., Wides, A., Tepper, N. and
Davidi, D., 2016. Sugar synthesis from CO 2 in Escherichia coli. Cell,
166(1), pp.115-125.

[2] Ebrahim, Ali, Joshua A. Lerman, Bernhard O. Palsson, and Daniel R.
Hyduke. "COBRApy: COnstraints-based reconstruction and analysis for
python." BMC systems biology 7, no. 1 (2013): 74.

[3] Cardoso, Joao, Kristian Jensen, Christian Lieven, Anne Sofie Laerke
Hansen, Svetlana Galkina, Moritz Emanuel Beber, Emre Ozdemir, Markus
Herrgard, Henning Redestig, and Nikolaus Sonnenschein. "Cameo: A Python
Library for Computer Aided Metabolic Engineering and Optimization of
Cell Factories." bioRxiv (2017): 147199.