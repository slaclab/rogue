.. _installing:

============================
Installing & Compiling Rogue
============================

This section covers supported installation and build workflows for Rogue.

After installation, continue with :doc:`/quick_start/index` for first-run
validation and basic workflow checks.

The recommended method for installing Rogue is through
:ref:`installing_miniforge` and
:ref:`installing_miniforge_build`.
If you choose to build Rogue from source instead of using Miniforge, the following list
is the recommendation for each operating system.

**Note:** Native source builds are currently supported on Linux and macOS arm64.
Windows users should use Ubuntu (WSL) or Docker.

* Linux - :ref:`installing_full_build`
* Windows - :ref:`installing_docker`
* Mac (arm64) - :ref:`installing_miniforge_build`

What To Explore Next
====================

- First-run validation and common checks: :doc:`/quick_start/index`
- Guided end-to-end workflows: :doc:`/tutorials/index`


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
