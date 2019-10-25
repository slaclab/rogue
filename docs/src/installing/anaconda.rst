.. _installing_anaconda:

==============================
Installing Rogue With Anaconda
==============================

The following instructions describe how to install a pre-built Rogue package inside an anaconda environment. These instructions are relevant for Linux, Ubuntu on Windows and MacOS.

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

Creating A Rogue Environment
============================

The next step is to create ana anaconda environment which includes the Rogue package.

.. code::

   $ conda create -n rogue_tag -c tidair-packages -c pydm-tag -c conda-forge -c tidair-tag rogue

The order of the args is important. tidair-tag is the channel from which the Rogue package is downloaded.

If you already have an anaconda environment that you would like to install Rogue into:

.. code::

   $ conda install -c tidair-packages -c pydm-tag -c conda-forge -c tidair-tag rogue

The above commands will install the latest version of Rogue from the master branch. If you want to insteall the pre-release version of Rogue, run the following:

.. code::

   $ conda create -n rogue_dev -c tidair-packages -c pydm-tag -c conda-forge -c tidair-dev rogue

Alternatively you can install a specific released version of Rogue:

.. code::

   $ conda create -n rogue_4.2.1 -c tidair-packages -c pydm-tag -c conda-forge -c tidair-tag rogue=v4.2.1

Using Rogue In Anaconda
=======================

No additional setup scripts need to be run Rogue in an anaconda environment. To activate and de-activate the Rogue environment you can use the following commands:

To activate:

.. code::

   $ conda activate rogue_tag

Replace rogue_tag with the name you used when creating your environment (rogue_dev or rogue_4.2.1).


To deactivate:

.. code::

   $ conda deactivate

Installing Rogue In Existing Environment
========================================

The following command is used to install Rogue inside and existing anaconda environment.


Updating Rogue In Anaconda
==========================

If you want to update Rogue, run the following command after activating the Rogue environment

.. code::

   $ conda update rogue -c tidair-tag

Replace tidair-tag with tidair-dev for pre-release

Deleting Anaconda Environment
=============================

Run the following commands to delete the anaconda environment.

.. code::

   $ conda env remove -n rogue_tag
