.. _installing_anaconda_build:

==============================
Building Rogue Inside Anaconda
==============================

This section provides instructions for downloading and building rogue inside an anaconda environment. These
instructions are relevant for Linux, Ubuntu on Windows and MacOS.

See MacOS section at the bottom for additional steps required for building rogue in MacOS.

See the section :ref:`installing_windows` for additional steps required for Windows.

Getting Anaconda
================

Download and install anaconda (or miniconda) if you don't already have it installed on your machine. Choose an install location with a lot of available diskspace (> 5GB). Anaconda appears to only work reliably in the bash shell. 

Go to https://www.anaconda.com/download to get the latest version of anaconda. Example steps for installing anaconda are included below:

.. code::

   $ wget https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh
   $ bash Anaconda3-5.3.0-Linux-x86_64.sh

You do not need to install visual studio.

Use the following command to add anaconda to your environment. This can be added to your .bash_profile.

.. code::

   $ source /path/to/my/anaconda3/etc/profile.d/conda.sh

Downloading Rogue & Creating Anaconda Environment
=================================================

The next step is to download rogue and create a rogue compatible anaconda environment.

.. code::

   $ conda activate
   $ conda install git
   $ git clone https://github.com/slaclab/rogue.git
   $ cd rogue

For Linux:

.. code::

   $ conda env create -n rogue_build -f conda.yml

For MacOS:

.. code::

   $ conda env create -n rogue_build -f conda_mac.yml


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

Special Steps For MacOS
=======================

In order to compile rogue in MacOS you first need to download an install an older version of the MacOS SDK

.. code::

   $ git clone https://github.com/phracker/MacOSX-SDKs
   $ sudo mv MacOSX-SDKs/MacOSX10.9.sdk /opt/

You must set the following environment variables to setup anaconda in build mode before creating and activating the rogue environment.

.. code::

   $ export CONDA_BUILD_SYSROOT=/opt/MacOSX10.9.sdk
   $ export CONDA_BUILD=1

