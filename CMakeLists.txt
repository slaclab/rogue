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
cmake_minimum_required(VERSION 3.10)
include(InstallRequiredSystemLibraries)

# Project name
project (rogue_pyrogue)

# C/C++
enable_language(C CXX)

# Set version from git tag
find_package(Git)
if (GIT_FOUND)
   execute_process (
      COMMAND ${GIT_EXECUTABLE} describe --tags --dirty
      OUTPUT_VARIABLE ROGUE_VERSION
      RESULT_VARIABLE ROGUE_VERSION_RESULT
      OUTPUT_STRIP_TRAILING_WHITESPACE
   )

   if (NOT ROGUE_VERSION_RESULT EQUAL 0 )
      set (ROGUE_VERSION "v0.0.0")
   endif()
else()
   set (ROGUE_VERSION "v0.0.0")
endif()

# Boost Configuration
set(Boost_USE_MULTITHREADED ON)
find_package(Boost 1.62 REQUIRED COMPONENTS system thread python3)

# Python Configuration
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

# Create rogue library
add_library(rogue SHARED "")

# Find sources
add_subdirectory("src/rogue")

# Set output to TOP/lib
set_target_properties(rogue PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/lib")

# Link to boost, python and bzip
TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC ${PYTHON_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC bz2)

# Create pyrogue library
add_library(pyrogue SHARED "")

# Find sources
add_subdirectory("src/pyrogue")

# Set output to TOP/python
set_target_properties(pyrogue PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/python")

# Link to rogue
TARGET_LINK_LIBRARIES(pyrogue LINK_PUBLIC rogue)

