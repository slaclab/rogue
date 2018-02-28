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

# Check cmake version
cmake_minimum_required(VERSION 2.8)
include(InstallRequiredSystemLibraries)

# Project name
project (rogue)

# C/C++
enable_language(C CXX)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x")

# Set version from git tag
find_package(Git)
if (GIT_FOUND)
   execute_process (
      COMMAND ${GIT_EXECUTABLE} describe --tags --dirty
      OUTPUT_VARIABLE ROGUE_VERSION
      OUTPUT_STRIP_TRAILING_WHITESPACE)
else()
   message(FATAL_ERROR "Git is required to build rogue")
endif()

# Boost Configuration
set(Boost_USE_MULTITHREADED ON)

# Boost may need help on SLAC machines
if (${BOOST_PATH})
   set(BOOST_ROOT:PATHNAME, ${BOOST_PATH})
endif()

# Find boost
find_package(Boost 1.58 REQUIRED COMPONENTS system thread python3)

# Find python3
find_package(PythonInterp 3 REQUIRED)
find_package(PythonLibs 3 REQUIRED)

# Configuration File
configure_file (
   "${PROJECT_SOURCE_DIR}/include/rogue/RogueConfig.in"
   "${PROJECT_BINARY_DIR}/RogueConfig.h"
)

# Add include directories
include_directories("${PROJECT_SOURCE_DIR}/include")
include_directories("${PROJECT_SOURCE_DIR}/drivers/include")
include_directories(${PROJECT_BINARY_DIR})
include_directories(${Boost_INCLUDE_DIRS})
include_directories(${PYTHON_INCLUDE_DIRS})

# Create rogue core library
add_library(rogue-core SHARED "")

# Find sources
add_subdirectory("src/rogue")

# Set output to TOP/lib
set_target_properties(rogue-core PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/lib")

# Link to boost, python and bzip
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${PYTHON_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC bz2)

# Create rogue python library
add_library(rogue SHARED "")

# Find sources
add_subdirectory("src")

# Set output to TOP/python, remove lib prefix
set_target_properties(rogue PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/python")
set_target_properties(rogue PROPERTIES PREFIX "")

# Link to rogue
TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC rogue-core)

