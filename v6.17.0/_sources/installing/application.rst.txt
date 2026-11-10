.. _installing_application:

=============================
Compiling A Rogue Application
=============================

The following describes how to compiled a c++ application against the Rogue libraries. 

The following is an example custom CMakeLists.txt which will setup the environment
for compiling application code using existing Rogue libraries. It is assumed
that the ROGUE_DIR environment variable points to the non-standard Rogue
location if not using an Miniforge environment, Docker or System install.

This CMakeLists.txt file assumes a **src** sub-directory exists with a single
.cpp file for each application being compiled. The following commands will
compile the applications:

.. code::

   $ mkdir build
   $ cd build
   $ cmake ..
   $ make

The outputs will be placed in a **bin** sub-directory.

.. code:: cmake

   # Add support for building in conda environment
   if (DEFINED ENV{CONDA_PREFIX})
      set(CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
      link_directories($ENV{CONDA_PREFIX}/lib)
   endif()

   # Check cmake version
   cmake_minimum_required(VERSION 3.5)
   include(InstallRequiredSystemLibraries)

   # Project name
   project (RssiSinK)

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

   # Set output directory
   set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/bin)

   # Compile each source
   file(GLOB APP_SOURCES ${PROJECT_SOURCE_DIR}/src/*.cpp)
   foreach (srcFile ${APP_SOURCES})
      get_filename_component(binName ${srcFile} NAME_WE)
      add_executable(${binName} ${srcFile})
      TARGET_LINK_LIBRARIES(${binName} LINK_PUBLIC ${ROGUE_LIBRARIES})
   endforeach ()

