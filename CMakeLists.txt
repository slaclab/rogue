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
project (rogue)

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
include_directories({Boost_INCLUDE_DIRS})

# Python Configuration
find_package(Boost 1.62 REQUIRED COMPONENTS system thread python3)

# Configuration File
configure_file (
   "RogueConfig.in"
   "include/rogue/RogueConfig.h"
)

# Set rogue library target
set(ROGUE_LIB "rogue_lib")
add_library(${ROGUE_LIB} SHARED "")
TARGET_LINK_LIBRARIES(${ROGUE_LIB} ${Boost_LIBRARIES})

# Set pyrogue library target
set(PYROGUE_LIB 3 REQURED)
add_library(${PYROGUE_LIB} SHARED "")
TARGET_LINK_LIBRARIES(${PYROGUE_LIB} ${Boost_LIBRARIES})

# Add source and include files
include_directories("include")
add_subdirectory("src/rogue")

