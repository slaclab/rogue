.. _custom_makefile:

Custom Module CMakeLists.txt
============================

The following is an example custom CMakeLists.txt which will setup the environment
for building a custom Rogue module using existing Rogue libraries. It is assumed
that the ROGUE_DIR environment variable points to the non-standard Rogue
location if not using an Anaconda environment, Docker or System install.

Replace MyModule with your module name globally in this file. 

This file assumes that the source file MyModule.cpp exists in the src
subdirectory relative to this file's location.  This file can be used to 
compile the :ref:`custom_sourcefile` described in this section.  This 
CMakeLists can be used to compile the custom module with the following commands:

.. code::

   $ mkdir build
   $ cd build
   $ cmake ..
   $ make

The output shared library MyModule.so will be created in the python
sub-directory. This directory will need to be included in the PYTHONPATH
environment variable.

.. code:: cmake

   # Add support for building in conda environment
   if (DEFINED ENV{CONDA_PREFIX})
      set(CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
      link_directories($ENV{CONDA_PREFIX}/lib)
   endif()

   # Check cmake version
   cmake_minimum_required(VERSION 3.5)
   include(InstallRequiredSystemLibraries)

   # Project name, Replace with your name
   project (MyModule)

   # C/C++
   enable_language(CXX)
   set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x -Wno-deprecated")

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

