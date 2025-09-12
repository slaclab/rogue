.. _installing_miniforge:

===============================
Installing Rogue With Miniforge
===============================

The following instructions describe how to install a pre-built Rogue package inside an miniforge environment. These instructions are relevant for Linux, Ubuntu on Windows and MacOS.

Windows installations will require you to install Ubuntu. Reference the section :ref:`installing_windows` for required steps. 
Mac is not currently supported for rogue, and a VM or docker image is needed. Proceed to :ref:`installing_docker`. 

Instructions for s3df setup are also available on `Confluence <https://confluence.slac.stanford.edu/spaces/ppareg/pages/591664140/Configure+miniforge+conda+and+Rogue+on+S3DF>`. 

Getting Miniforge
================

Download and install miniforge if you don't already have it installed on your machine. Choose an install location with a lot of available diskspace (> 5GB). 
Miniforge appears to only work reliably in the bash shell.

*Linux*

.. code::

   $ wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
   $ bash Miniforge3-Linux-x86_64.sh

Use the following command to add miniforge to your environment. This can be added to your .bash_profile.

.. code::

   $ source /path/to/my/miniforge3/etc/profile.d/conda.sh

It is important to use the latest conda solver:

.. code::

    $ conda activate
    $ conda config --set channel_priority strict
    $ conda install -n base conda-libmamba-solver
    $ conda config --set solver libmamba

Creating A Rogue Environment
============================

The next step is to create an miniforge environment which includes the Rogue package.

.. code::

   $ conda create -n rogue_tag -c tidair-tag -c conda-forge rogue

The order of the args is important. tidair-tag is the channel from which the Rogue package is downloaded.

If you already have an miniforge environment that you would like to install Rogue into:

.. code::

   $ conda install -c tidair-tag -c conda-forge rogue

Alternatively you can install a specific released version of Rogue:

.. code::

   $ conda create -n rogue_v6.5.0 -c conda-forge -c tidair-tag rogue=v6.5.0

Using Rogue In Miniforge
=======================

No additional setup scripts need to be run Rogue in an miniforge environment. To activate and de-activate the Rogue environment you can use the following commands:

To activate:

.. code::

   $ conda activate rogue_tag

Replace rogue_tag with the name you used when creating your environment (e.g. rogue_v6.5.0).


To deactivate:

.. code::

   $ conda deactivate

Installing Rogue In Existing Environment
========================================

The following command is used to install Rogue inside and existing miniforge environment.


Updating Rogue In Miniforge
==========================

If you want to update Rogue, run the following command after activating the Rogue environment

.. code::

   $ conda update rogue -c tidair-tag

Deleting Miniforge Environment
=============================

Run the following commands to delete the miniforge environment.

.. code::

   $ conda env remove -n rogue_tag

