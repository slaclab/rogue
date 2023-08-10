.. _installing_anaconda_build:

==============================
Building Rogue Inside Anaconda
==============================

This section provides instructions for downloading and building rogue inside an anaconda environment. These
instructions are relevant for Linux

Getting Anaconda
================

Download and install anaconda (or miniconda) if you don't already have it installed on your machine. Choose an install location with a lot of available diskspace (> 5GB). Anaconda appears to only work reliably in the bash shell.

Go to https://www.anaconda.com/download to get the latest version of anaconda. Example steps for installing anaconda are included below:

.. code::

   $ wget https://repo.anaconda.com/archive/Anaconda3-{version}-Linux-x86_64.sh
   $ bash Anaconda3-{version}-Linux-x86_64.sh

Use the following command to add anaconda to your environment. This can be added to your .bash_profile.

.. code::

   $ source /path/to/my/anaconda3/etc/profile.d/conda.sh

Set your local anaconda to use the update solver:

.. code::

    $ conda activate
    $ conda config --set channel_priority strict
    $ conda install -n base conda-libmamba-solver
    $ conda config --set solver libmamba

Downloading Rogue & Creating Anaconda Environment
=================================================

The next step is to download rogue and create a rogue compatible anaconda environment.

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ conda activate
   $ conda env create -n rogue_build -f conda.yml

You now have an anaconda environment named rogue_build which contains all of the packages required to build and run rogue.

To activate this environment:

.. code::

   $ conda activate rogue_build

Building Rogue In Anaconda
==========================

Once the rogue environment is activated, you can build and install rogue

.. code::

   $ mkdir build
   $ cd build
   $ cmake ..
   $ make
   $ make install

The Rogue build system will automatically detect that it is in a conda environment and it will be installed
within the anaconda rogue environment.

Using Rogue In Anaconda
=======================

No additional setup scripts need to be run rogue in an anaconda environment. To activate and de-activate the rogue environment you can use the following commands:

To activate:

.. code::

   $ conda activate rogue_build

To deactivate:

.. code::

   $ conda deactivate

Updating Rogue In Anaconda
==========================

If you want to update and re-install rogue, run the following commands.

.. code::

   $ cd rogue
   $ rm -rf build
   $ git pull
   $ mkdir build
   $ cd build
   $ cmake ..
   $ make
   $ make install

Deleting Anaconda Environment
=============================

Run the following commands to delete the anaconda environment.

.. code::

   $ conda env remove -n rogue_build

