.. _installing_miniforge_build:

==============================
Building Rogue Inside Miniforge
==============================

This section provides instructions for downloading and building rogue inside an miniforge environment. These
instructions are relevant for Linux

Getting Miniforge
==================

Download and install miniforge if you don't already have it installed on your machine. Choose an install location with a lot of available diskspace (> 5GB). Miniforge appears to only work reliably in the bash shell.

.. code::

   $ wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
   $ bash Miniforge3-Linux-x86_64.sh

Use the following command to add miniforge to your environment. This can be added to your .bash_profile.

.. code::

   $ source /path/to/my/miniforge3/etc/profile.d/conda.sh

Set your local miniforge to use the update solver:

.. code::

    $ conda activate
    $ conda config --set channel_priority strict
    $ conda install -n base conda-libmamba-solver
    $ conda config --set solver libmamba

Downloading Rogue & Creating Miniforge Environment
===================================================

The next step is to download rogue and create a rogue compatible miniforge environment.

.. code::

   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue
   $ conda activate
   $ conda env create -n rogue_build -f conda.yml

You now have an miniforge environment named rogue_build which contains all of the packages required to build and run rogue.

To activate this environment:

.. code::

   $ conda activate rogue_build

Building Rogue In Miniforge
============================

Once the rogue environment is activated, you can build and install rogue

.. code::

   $ mkdir build
   $ cd build
   $ cmake ..
   $ make -j$(nproc)
   $ make install

The Rogue build system will automatically detect that it is in a conda environment and it will be installed
within the miniforge rogue environment.

Using Rogue In Miniforge
=========================

No additional setup scripts need to be run rogue in an miniforge environment. To activate and de-activate the rogue environment you can use the following commands:

To activate:

.. code::

   $ conda activate rogue_build

To deactivate:

.. code::

   $ conda deactivate

Updating Rogue In Miniforge
============================

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

Deleting Miniforge Environment
===============================

Run the following commands to delete the miniforge environment.

.. code::

   $ conda env remove -n rogue_build

