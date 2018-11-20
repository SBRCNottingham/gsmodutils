gsmodutils - a genome scale model development and testing framework.
####################################################################


|docs| |Build Status| |Dev Build Status| |Coverage Status| |PyPI| |wheel| |supported-versions|

.. |Build Status| image:: https://api.travis-ci.org/SBRCNottingham/gsmodutils.svg?branch=master
   :target: https://travis-ci.org/SBRCNottingham/gsmodutils
.. |Dev Build Status| image:: https://api.travis-ci.org/SBRCNottingham/gsmodutils.svg?branch=develop
   :target: https://travis-ci.org/SBRCNottingham/gsmodutils
.. |Coverage Status| image:: https://codecov.io/gh/SBRCNottingham/gsmodutils/branch/master/graph/badge.svg?token=tZyixhlZtJ
   :target: https://codecov.io/github/SBRCNottingham/gsmodutils
.. |PyPI| image:: https://badge.fury.io/py/gsmodutils.svg
   :target: https://pypi.python.org/pypi/gsmodutils
.. |docs| image:: https://readthedocs.org/projects/gsmodutils/badge/?style=flat
    :target: https://gsmodutils.readthedocs.io
    :alt: Documentation Status
.. |wheel| image:: https://img.shields.io/pypi/wheel/gsmodutils.svg
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/gsmodutils
.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/gsmodutils.svg
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/gsmodutils

Initially developed by the Nottingham SBRC for use with their genome scale models.

Design goals:


- **Portability and interoperability.** models come in different formats - cobra JSON, matlab, SBML, ScrumPy etc. The tool needs to be able to export and import models in these formats. This allows users to leverage tools not just in the python development stack, such as CobraPy but also other strain design methods from the likes of Matlab and OptKnock. This is achieved through a command line api that allows the export of files in to a variety of formats. This ensures that good standards can be followed and maintained.

- **Reusability of previous designs.** The constraints, reactions, genes and metabolites for different designs can be a headache to manage. Generally, a base strain will exist and users will modify this over a long period of time. Likewise, designs the exploit existing hetrologous pathways or optimisations can be reused through an inherited design approach.

- **Testability of models.** The validity of a model is a difficult aspect to measure. Constant manual curation in order to match experimental data requires users to check conditions. For this reason a testing framework is adopted allowing models to maintain conditions of validation. By default added growth constraints and designs can be tested. Users can also write tests in python and JSON to ensure that essential pathways are maintained and validation against experimental data is met.

- **Sharability.** The design of the project uses flat files rather than database systems. Whilst this looses some power it ensures that any models developed can be shared easily through distributed source control software like Git and mercurial. Similarly, in the future the project aims to allow models to be distributed via Docker containers allowing controlled environments to improve collaboration where users require more than just a model to perform complex analysis.


Installation
------------
To install the latest release from pip:

.. code-block::

    pip install gsmodutils

To install this software clone the git repository and type:

.. code-block::

    pip install -r requriements.txt
    python setup.py install
    
To run the tests for this project, install pytest and, from the project root directory simply run

.. code-block::

    pytest
    
gsmodutils is fully compatible with python 2.7+ and python 3.6+.
This software has been tested on linux (Ubuntut, manjaro/arch), windows and MacOSX.


Change notes
------------

**Version 0.0.3**:


Added `gsmodutils.utils.design_annoation` decorator for annotating python based designs.
Fixed GsmodutilsModel.save_model for sbml models (it used to save it as a matlab).

**Version 0.0.2:**

Changed method for test ids to separators being "::" for example "test_pytest.py::test_func" or "design::design_id"

Major refactor of test loading classes:

* CLI and gsmodutils.test.tester class API remains the same
* Tests are now encapsulated around TestInstance classes
* Hierarchy of logs is stored
* Encapsulates individual tests better
* Can run child tests in isolation
* Allows access to python tests with runtime specified models (useful for python based interaction)

GSModutilsModel class to allow the selection of specific tests related to the loaded model.

Usage
-----
Please read the user guide in the docs_!

.. _docs: https://gsmodutils.readthedocs.io

See also
-----------

This project would be nothing without other great open source software projects.
In particular, we would like to draw attention to ```cameo``` and ```cobrapy```.
These projects offer a wide array of functionality for FBA and other constraints based
analysis within the python open source stack.

Contributors
------------
James Gilbert  University of Nottingham - main software developer.
Nicole Pearcy - Testing, ideas and knowledge of genome scale models.

If you would like to collaborate, please get in touch!

Acknowledgements
================

This project was developed as part of the Synthetic Biology Research Centre at the University of Nottingham.

This work was supported by the UK Biotechnology and Biological Sciences Research Council (BBSRC) grants BB/L013940/1,  BB/K00283X/1 and BB/L502030/1.


.. Image:: https://www.nottingham.ac.uk/SiteElements/Images/Base/logo.png
    :height: 80px


.. Image:: https://bbsrc.ukri.org/bbsrc/cache/file/602A834A-B296-4FF0-AC67AA8C99E7D0E4_source.gif
    :height: 80px

.. Image:: http://sbrc-nottingham.ac.uk/images-multimedia/sbrcweblogo80.jpg
    :height: 80px
