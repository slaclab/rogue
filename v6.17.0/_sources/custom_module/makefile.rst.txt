.. _custom_makefile:

==========================
Building The Custom Module
==========================

The example below shows a custom ``CMakeLists.txt`` for building a Rogue module
against an existing Rogue installation. ``ROGUE_DIR`` can be used when Rogue
is installed in a non-standard location rather than in Miniforge, Docker, or a
system path.

Replace MyModule with your module name globally in this file.

This file assumes that ``MyModule.cpp`` exists in the **src** subdirectory
relative to the project root. It can be used to compile the
:ref:`custom_sourcefile` with the following commands:

.. code-block:: bash

   $ mkdir build
   $ cd build
   $ cmake ..
   $ make

The output shared library ``MyModule.so`` will be created in the **python**
subdirectory. That directory needs to be included in ``PYTHONPATH``.

.. code:: cmake

   # Source for CMakeLists.txt

   # Add support for building in conda environment
   if (DEFINED ENV{CONDA_PREFIX})
      set(CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
      link_directories($ENV{CONDA_PREFIX}/lib)
   endif()

   # Check cmake version
   cmake_minimum_required(VERSION 3.15)
   include(InstallRequiredSystemLibraries)

   # Project name, Replace with your name
   project (MyModule)

   # C/C++
   enable_language(CXX)
   set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-deprecated")
   add_definitions(-D__STDC_FORMAT_MACROS)

   # Rogue is built as C++14; match it so the ABI is compatible. Do not also
   # pass a -std= flag in CMAKE_CXX_FLAGS -- CMAKE_CXX_STANDARD is the single
   # source of truth for the language standard.
   set(CMAKE_CXX_STANDARD 14)
   set(CMAKE_SKIP_BUILD_RPATH TRUE)
   set(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)
   set(CMAKE_INSTALL_RPATH_USE_LINK_PATH FALSE)

   #####################################
   # Find Rogue & Support Libraries
   #####################################
   if (DEFINED ENV{ROGUE_DIR})
      set(Rogue_DIR $ENV{ROGUE_DIR}/lib)
   else()
      set(Rogue_DIR ${CMAKE_PREFIX_PATH}/lib)
   endif()
   find_package(Rogue)

   #####################################
   # Setup build
   #####################################

   # Include files
   include_directories(${ROGUE_INCLUDE_DIRS})

   # Create rogue python library, point to your source file
   add_library(MyModule SHARED src/MyModule.cpp)

   # Set output to TOP/lib, remove lib prefix
   set_target_properties(MyModule PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/python)
   set_target_properties(MyModule PROPERTIES PREFIX "")

   # Link to rogue core
   TARGET_LINK_LIBRARIES(MyModule LINK_PUBLIC ${ROGUE_LIBRARIES})

How ``find_package(Rogue)`` Works
=================================

``find_package(Rogue)`` loads ``RogueConfig.cmake``, which Rogue generates and
installs into ``<install>/lib`` at build time. That file rediscovers Rogue's own
dependencies (Boost, Python, NumPy, ZeroMQ, BZip2) and then defines the variables
this ``CMakeLists.txt`` consumes:

- ``ROGUE_INCLUDE_DIRS`` -- Rogue headers **plus** all dependency include paths.
- ``ROGUE_LIBRARIES`` -- the Rogue core library **plus** all dependency libraries.

Use those two for the common case (a Python-loadable module or an application
that links the full stack). Variants that expose only Rogue itself
(``ROGUE_INCLUDE_ONLY`` / ``ROGUE_LIBRARIES_ONLY``), along with ``ROGUE_DIR`` and
``ROGUE_VERSION``, are documented in :ref:`custom_rogueconfig`.

``Rogue_DIR`` tells CMake which directory contains ``RogueConfig.cmake``. The
example resolves it from the ``ROGUE_DIR`` environment variable (set by
``setup_rogue.sh``) or from ``CMAKE_PREFIX_PATH`` for conda/system installs.

.. note::

   If configuration fails with ``Could not find a package configuration file
   provided by "Rogue"``, point CMake at the install explicitly, e.g.
   ``export ROGUE_DIR=/path/to/rogue`` (the directory whose ``lib`` subdirectory
   holds ``RogueConfig.cmake``), or pass ``-DRogue_DIR=/path/to/rogue/lib`` on
   the ``cmake`` command line.

What To Explore Next
====================

- Variables exported by ``RogueConfig.cmake``: :ref:`custom_rogueconfig`
- Custom module source structure: :ref:`custom_sourcefile`
- Wrapping the resulting module in PyRogue: :ref:`custom_wrapper`
