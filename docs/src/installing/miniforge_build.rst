.. _installing_miniforge_build:

===============================
Building Rogue Inside Miniforge
===============================

Building Rogue from source inside a Miniforge environment is the recommended
workflow when you need local source changes, documentation work, or
development against the current repository state.

These instructions are relevant for Linux and macOS arm64.

Prerequisites
=============

On macOS, install Apple Command Line Tools before creating the environment:

.. code::

   $ xcode-select --install

Getting Miniforge
==================

Download and install Miniforge if you do not already have it installed. Choose
an install location with adequate free disk space, typically more than 5 GB.
Miniforge generally works best from a Bash shell.

*Linux*

.. code::

   $ wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
   $ bash Miniforge3-Linux-x86_64.sh

*macOS (arm64)*

.. code::

   $ curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
   $ bash Miniforge3-MacOSX-arm64.sh

Use the following command to add Miniforge to your shell environment. This can
be added to your ``.bash_profile``.

.. code::

   $ source /path/to/my/miniforge3/etc/profile.d/conda.sh

Set your local Miniforge to use the current solver:

.. code::

    $ conda activate
    $ conda config --set channel_priority strict
    $ conda install -n base conda-libmamba-solver
    $ conda config --set solver libmamba

Downloading Rogue & Creating Miniforge Environment
==================================================

The next step is to clone Rogue and create a compatible Miniforge environment.

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ conda activate
   $ conda env create -n rogue_build -f conda.yml

You now have a Miniforge environment named ``rogue_build`` containing the
packages required to build and run Rogue.

You can alternatively clone the repository with
``git clone git@github.com:slaclab/rogue.git``.
To activate this environment:

.. code::

   $ conda activate rogue_build

Building Rogue In Miniforge
===========================

Once the environment is activated, build and install Rogue:

.. code::

   $ mkdir build
   $ cd build
   $ cmake ..
   $ make 
   $ make install

The Rogue build system automatically detects the Conda environment and installs
Rogue into that Miniforge environment.

Using Rogue In Miniforge
========================

No additional setup script is needed inside a Miniforge environment. Activate
and deactivate the environment with the usual Conda commands:

To activate:

.. code::

   $ conda activate rogue_build

To deactivate:

.. code::

   $ conda deactivate

Updating Rogue In Miniforge
===========================

If you want to update and reinstall Rogue, run the following commands:

.. code::

   $ cd rogue
   $ rm -rf build
   $ git pull
   $ mkdir build
   $ cd build
   $ cmake ..
   $ cmake --build .
   $ make install

Building And Viewing The Docs
=============================

If edits are made to the C++ or Python source files, rebuild Rogue before
expecting those changes to appear in generated documentation output.

.. code::

   # build the docs
   $ cd ../docs/
   $ make clean html

   # view output on web browser
   $ open build/html/index.html

Deleting Miniforge Environment
==============================

Run the following command to delete the Miniforge environment.

.. code::

   $ conda env remove -n rogue_build
