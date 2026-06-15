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
   set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x -Wno-deprecated")
   add_definitions(-D__STDC_FORMAT_MACROS)

   SET(CMAKE_CXX_STANDARD 14)
   SET(CMAKE_SKIP_BUILD_RPATH TRUE)
   SET(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)
   SET(CMAKE_INSTALL_RPATH_USE_LINK_PATH FALSE)

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

What To Explore Next
====================

- Custom module source structure: :ref:`custom_sourcefile`
- Wrapping the resulting module in PyRogue: :ref:`custom_wrapper`
