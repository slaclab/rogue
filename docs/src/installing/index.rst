.. _installing:

============================
Installing & Compiling Rogue
============================

Rogue supports several installation and build workflows, depending on whether
you want a prebuilt package, a source build, or a containerized runtime.

Most users should start with a Miniforge-based workflow. It gives Rogue a
managed Python environment, keeps dependencies predictable, and matches how the
project is commonly developed and tested.

In practice there are three main paths:

- Install a prebuilt Rogue package into Miniforge:
  :ref:`installing_miniforge`
- Build Rogue from source inside Miniforge:
  :ref:`installing_miniforge_build`
- Build Rogue from source outside Miniforge:
  :ref:`installing_full_build`

Recommended choices by platform are:

- Linux: :ref:`installing_miniforge` or :ref:`installing_miniforge_build`
- macOS arm64: :ref:`installing_miniforge_build`
- Windows: :ref:`installing_windows`, then use
  :ref:`installing_miniforge` inside WSL2 or use
  :ref:`installing_docker`

Native source builds outside Miniforge are mainly for environments that already
have their own dependency and deployment model. For most application users,
Miniforge is the simpler path.

What This Section Covers
========================

- Miniforge install and source-build workflows
- Native source builds
- Docker-based usage
- Platform-specific notes such as WSL2 and firewall constraints
- Packaging-oriented notes such as Yocto integration and external application
  builds

Related Topics
==============

- Guided end-to-end workflows: :doc:`/tutorials/index`
- PyRogue tree architecture and lifecycle: :doc:`/pyrogue_tree/index`


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
