# ----------------------------------------------------------------------------
# Title      : ROGUE CMAKE Control
# ----------------------------------------------------------------------------
# File       : CMakeLists.txt
# Created    : 2018-02-27
# ----------------------------------------------------------------------------
# This file is part of the rogue software package. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software package, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

# Add support for building in conda environment
if (DEFINED ENV{CONDA_PREFIX})
   set(CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
endif()

# Check cmake version
cmake_minimum_required(VERSION 3.5)
include(InstallRequiredSystemLibraries)

# Project name
project (rogue)

# C/C++
enable_language(CXX)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x")

# Set version from git tag
find_package(Git)
if (GIT_FOUND)
   execute_process (
      COMMAND ${GIT_EXECUTABLE} describe --tags --dirty
      OUTPUT_VARIABLE ROGUE_VERSION
      OUTPUT_STRIP_TRAILING_WHITESPACE)

   string(REGEX MATCH "^v([0-9]+)\\.([0-9]+)" ROGUE_SOVER ${ROGUE_VERSION})
else()
   message(FATAL_ERROR "Git is required to build rogue!")
endif()

#####################################
# Find python3
#####################################
set(DO_PYTHON 0)

find_package(PythonInterp 3.6)

if (PYTHONINTERP_FOUND)
   find_package(PythonLibs 3.6)

   if (PYTHONLIBS_FOUND)
      set(DO_PYTHON 1)
   endif()
endif()

#####################################
# Boost Configuration
#####################################
set(Boost_USE_MULTITHREADED ON)

# Boost may need help on SLAC machines
set(BOOST_ROOT:PATHNAME $ENV{BOOST_PATH})

# First try standard suffix for boost
if (DO_PYTHON)
find_package(Boost 1.58 COMPONENTS system thread python3)
endif()

# Next try Debian/Ubuntu suffix for boost
if ((NOT Boost_FOUND) AND DO_PYTHON)
   find_package(Boost 1.58 COMPONENTS system thread python-py36)
endif()

# Next try Mac with homebrew boost/python36
if ((NOT Boost_FOUND) AND DO_PYTHON)
   find_package(Boost 1.58 COMPONENTS system thread python36)
endif()

# Try without python
if (NOT Boost_FOUND)
   set(DO_PYTHON 0)
   find_package(Boost 1.58 COMPONENTS system thread)
endif()

# Nothing worked
if (NOT Boost_FOUND)
   message(FATAL_ERROR "Failed to find boost libraries!")
endif()

#####################################
# Optional EPICS V3
#####################################
if(DO_PYTHON AND DEFINED ENV{EPICS_BASE})
   set(DO_EPICS_V3 1)
   set(EPICSV3_BASE_DIR  $ENV{EPICS_BASE})
   set(EPICSV3_LIB_DIR   ${EPICSV3_BASE_DIR}/lib/rhel6-x86_64 )
   set(EPICSV3_INCLUDES  ${EPICSV3_BASE_DIR}/include
                         ${EPICSV3_BASE_DIR}/include/compiler/gcc 
                         ${EPICSV3_BASE_DIR}/include/os/Linux)
   set(EPICSV3_LIBRARIES ${EPICSV3_LIB_DIR}/libcas.so 
                         ${EPICSV3_LIB_DIR}/libca.so 
                         ${EPICSV3_LIB_DIR}/libCom.so 
                         ${EPICSV3_LIB_DIR}/libgdd.so )
else()
   set(DO_EPICS_V3 0)
endif()

#####################################
# Setup build
#####################################

# Configuration File
configure_file (
   ${PROJECT_SOURCE_DIR}/include/rogue/RogueConfig.in
   ${PROJECT_BINARY_DIR}/RogueConfig.h
)

# Add include directories
include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(${PROJECT_SOURCE_DIR}/drivers/include)
include_directories(${PROJECT_BINARY_DIR})
include_directories(${Boost_INCLUDE_DIRS})
include_directories(${PYTHON_INCLUDE_DIRS})
include_directories(${EPICSV3_INCLUDES})

SET(CMAKE_SHARED_LIBRARY_SUFFIX ".so")

# Create rogue core library
add_library(rogue-core SHARED "")

# Find rogue core sources
add_subdirectory(src/rogue)

# Set output to TOP/lib
set_target_properties(rogue-core PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/lib 
                                 VERSION ${ROGUE_VERSION} SOVERSION ${ROGUE_SOVER})

# Link rogue core to boost, python and bzip
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${PYTHON_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${EPICSV3_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC bz2)

if (DO_PYTHON)

   # Create rogue python library
   add_library(rogue SHARED "")

   # Find python package sources
   add_subdirectory(src)

   # Set output to TOP/python, remove lib prefix
   set_target_properties(rogue PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/python)
   set_target_properties(rogue PROPERTIES PREFIX "")

   # Link to rogue core
   TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC rogue-core)

else()
   add_definitions( -DNO_PYTHON )
endif()


# Setup configuration file
set(CONF_INCLUDE_DIRS ${PROJECT_SOURCE_DIR}/include)
set(CONF_LIBRARIES    ${PROJECT_SOURCE_DIR}/lib/librogue-core.so.${ROGUE_SOVER})

# Create the config file
configure_file(RogueConfig.cmake.in ${PROJECT_SOURCE_DIR}/lib/RogueConfig.cmake @ONLY)

message("")
message("----------------------------------------------------------------------")
message("-- Success!")
message("")
message("-- Rogue Version: ${ROGUE_VERSION}")
message("")
message("-- Found boost: ${Boost_INCLUDE_DIRS}")
message("")

if (DO_PYTHON)
   message("-- Found python: ${PYTHON_LIBRARIES}")
else()
   message("-- Compiling without python!")
endif()

message("")

if (DO_EPICS_V3)
   message("-- Found EPICS V3: ${EPICSV3_BASE_DIR}")
else()
   message("-- EPICS V3 not included!")
endif()

message("----------------------------------------------------------------------")
message("")

