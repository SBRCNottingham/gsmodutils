Sharing projects with docker
============================

This section describes how to share a gsmodutils project inside a docker container.

The objective is to have code for testing models, data for their validation and the framework for running models written  in a "write once run anywhere" fashion.

Ideally, even if a platform for running a model is considerably out of date it should produce the same results on new software.

Unfortunately this isn't always the case. Packaging a constraints based model, with associated software within the same working environment ensures that the results should be reproducable, providing other users can install docker containers.

To install docker on your system please consult the documentation at https://docs.docker.com

Creating a docker container
---------------------------

To create a new docker container (with the latest gsmodutils setup scripts, use the docker utility.

.. code-block:: guess

    $ gsmodutils docker --overwrite

This will overwrite an existing ``Dockerfile`` and ``requirements.txt``.
If you have additional software requirements (such as python packages) you will want to modify these.
If you have large data files in your project that do not need to be shared, consider editing your ``Dockerfile`` to
ignore these to reduce the size of any resulting images.

Now to create a docker container use the build command

.. code-block:: guess

    $ docker build -t="example_project" <path_to_gsmodutils_project>

This will install the required python components for gsmodutils.

Running a docker container
--------------------------
gsmodutils just provides the basic dockerfile. In future iterations this may be changes.
To use code inside a docker image, run the command

.. code-block:: guess

    $ docker run -it <command>

For example, to load an ipython shell run:

.. code-block:: guess

    $ docker run -it example_project ipython

You might wish to get the project info:

.. code-block:: guess

    $ docker run -it example_project gsmodutils info
    --------------------------------------------------------
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
    ----------------------------------------------------------

Another example might be to run the gsmodutils test inside this portable environement:

.. code-block:: guess

    $ docker run -it example_project gsmodutils test
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

Sharing and loading gsmodutils docker images
--------------------------------------------

To share a project with users, first build it following the steps above. When the project is built use the command:

.. code-block:: guess

    $ docker save example_project -o example_project.tar

This saves the sharable docker container. When this tarball is transferred to another user, they can load the image with the command:

.. code-block:: guess

    $ docker load -i example_project.tar

The imported image will then allow the above commands to run with the same environmental settings. This should allow you to share your models in a way that allows results to be replicated without worrying about the software.