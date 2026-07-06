.. _custom_rogueconfig:

=============================
The RogueConfig.cmake Package
=============================

When Rogue is built, it generates a CMake package configuration file,
``RogueConfig.cmake``, and installs it into ``<install>/lib``. Downstream
projects load it with ``find_package(Rogue)`` (see :ref:`custom_makefile`) to
compile and link against an existing Rogue installation without hard-coding any
paths.

This page documents the variables that ``RogueConfig.cmake`` defines so you can
choose the right ones for your project.

What It Does
============

``RogueConfig.cmake`` re-runs the same dependency discovery that Rogue itself
uses at build time. It locates:

- Python 3 and NumPy (skipped if Rogue was built with ``-DNO_PYTHON=1``)
- Boost (including the Boost.Python component)
- ZeroMQ
- BZip2

It then exposes the results through the variables below.

Exported Variables
==================

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Variable
     - Meaning
   * - ``ROGUE_INCLUDE_DIRS``
     - Rogue's own include directory **plus** the include directories of every
       dependency (Boost, Python, NumPy, ZeroMQ, BZip2). Use this for
       ``include_directories()`` in the common case.
   * - ``ROGUE_LIBRARIES``
     - The Rogue core library **plus** every dependency library. Use this for
       ``target_link_libraries()`` in the common case.
   * - ``ROGUE_INCLUDE_ONLY``
     - Only Rogue's own include directory, without dependency includes.
   * - ``ROGUE_LIBRARIES_ONLY``
     - Only the Rogue core library, without dependency libraries.
   * - ``ROGUE_DIR``
     - The Rogue installation directory.
   * - ``ROGUE_VERSION``
     - The installed Rogue version string (from the git tag at build time).
   * - ``NO_PYTHON``
     - Set when Rogue was built with ``-DNO_PYTHON=1``. When true, Boost/Python
       discovery is skipped and ``-DNO_PYTHON`` is added to the compile
       definitions so your sources can guard Python bindings with
       ``#ifndef NO_PYTHON``.

Which Variables To Use
======================

- **Python-loadable modules and full applications** (the usual case): use
  ``ROGUE_INCLUDE_DIRS`` and ``ROGUE_LIBRARIES``. They carry everything needed to
  compile against Rogue headers and link the full stack.
- **Linking against only the Rogue core** (for example when your project already
  manages Boost/Python/ZeroMQ/BZip2 itself, or for a ``-DNO_PYTHON`` C++ build):
  use ``ROGUE_INCLUDE_ONLY`` and ``ROGUE_LIBRARIES_ONLY`` and add the
  dependencies you need explicitly.

Locating the Config File
=========================

``find_package(Rogue)`` needs to know which directory holds
``RogueConfig.cmake`` (always ``<install>/lib``). Set ``Rogue_DIR`` to that
directory, or set the ``ROGUE_DIR`` environment variable to the install root.
``setup_rogue.sh`` (generated for local and custom installs) exports
``ROGUE_DIR`` for you; conda and system installs are found through
``CMAKE_PREFIX_PATH``.

If configuration fails with ``Could not find a package configuration file
provided by "Rogue"``, set one of those variables explicitly:

.. code-block:: bash

   # Either point at the install root via the environment variable...
   export ROGUE_DIR=/path/to/rogue

   # ...or pass the lib directory directly to cmake:
   cmake .. -DRogue_DIR=/path/to/rogue/lib

What To Explore Next
====================

- The downstream ``CMakeLists.txt`` that consumes these variables: :ref:`custom_makefile`
- Custom module source structure: :ref:`custom_sourcefile`
