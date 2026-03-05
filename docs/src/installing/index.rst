.. _installing:

============================
Installing & Compiling Rogue
============================

Legacy Status
=============

This is a legacy page retained during migration.
This page is a top-level documentation entry for install/compile workflows.

This section describes how to obtain and install Rogue. 
After installation is completed, consider following our :doc:`/getting_started/index` guide to learn the basics. 

The recommended method for installing rogue is through :ref:`installing_miniforge` and
:ref:`installing_miniforge_build`.
If you chose to build rogue from source instead of using miniforge, the following list 
is the recommendation for each operating system.

**Note:** Native source builds are currently supported on Linux and macOS arm64.
Windows users should use Ubuntu (WSL) or Docker.

* Linux - :ref:`installing_full_build`
* Windows - :ref:`installing_docker`
* Mac (arm64) - :ref:`installing_miniforge_build`


.. toctree::
   :maxdepth: 1
   :caption: Install Options:

   miniforge
   miniforge_build
   docker
   build
   application
   firewall
   windows
   yocto
