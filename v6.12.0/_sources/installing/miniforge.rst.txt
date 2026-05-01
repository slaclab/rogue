.. _installing_miniforge:

===============================
Installing Rogue With Miniforge
===============================

A pre-built Rogue package can be installed into a Miniforge environment. This
is the simplest way to get a working Rogue installation on Linux or on Ubuntu
running under Windows WSL2.

Use this when:

- You do not need to modify Rogue itself,
- You want the fastest path to a usable environment,
- Or you want dependency management handled by Miniforge.

Windows installations require Ubuntu under WSL2. See
:ref:`installing_windows`.

For macOS arm64, the preferred path is to build from source inside Miniforge
using :ref:`installing_miniforge_build`.

Instructions for S3DF setup are also available on
`Confluence <https://confluence.slac.stanford.edu/spaces/ppareg/pages/591664140/Configure+miniforge+conda+and+Rogue+on+S3DF>`_.

Getting Miniforge
=================

Download and install Miniforge if you do not already have it installed. Choose
an install location with adequate free disk space, typically more than 5 GB.
Miniforge generally works best from a Bash shell.

*Linux*

.. code::

   $ wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
   $ bash Miniforge3-Linux-x86_64.sh

Use the following command to add Miniforge to your shell environment. This can
be added to your ``.bash_profile``.

.. code::

   $ source /path/to/my/miniforge3/etc/profile.d/conda.sh

It is important to use the current Conda solver:

.. code::

    $ conda activate
    $ conda config --set channel_priority strict
    $ conda install -n base conda-libmamba-solver
    $ conda config --set solver libmamba

Creating A Rogue Environment
============================

The next step is to create a Miniforge environment that includes the Rogue
package.

.. code::

   $ conda create -n rogue_tag -c tidair-tag -c conda-forge rogue

The order of the channels is important. ``tidair-tag`` is the channel from
which the Rogue package is downloaded.

If you already have a Miniforge environment and want to install Rogue into it:

.. code::

   $ conda install -c tidair-tag -c conda-forge rogue

Alternatively you can install a specific released version of Rogue:

.. code::

   $ conda create -n rogue_v6.5.0 -c conda-forge -c tidair-tag rogue=v6.5.0

Using Rogue In Miniforge
========================

No additional setup script is needed inside a Miniforge environment. Activate
and deactivate the environment with the usual Conda commands:

To activate:

.. code::

   $ conda activate rogue_tag

Replace ``rogue_tag`` with the environment name you chose, such as
``rogue_v6.5.0``.


To deactivate:

.. code::

   $ conda deactivate

Installing Rogue In Existing Environment
========================================

The following command installs Rogue into an existing Miniforge environment:

.. code::

   $ conda activate my_existing_env
   $ conda install -c tidair-tag -c conda-forge rogue


Updating Rogue In Miniforge
===========================

If you want to update Rogue, run the following command after activating the
environment:

.. code::

   $ conda update rogue -c tidair-tag

Deleting Miniforge Environment
==============================

Run the following command to delete the Miniforge environment.

.. code::

   $ conda env remove -n rogue_tag
