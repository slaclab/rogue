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
set(BOOST_ROOT:PATHNAME ${BOOST_PATH})

# First try standard suffix
find_package(Boost 1.58 COMPONENTS system thread python3)

# Next try Debian/Ubuntu suffix
if (NOT Boost_FOUND)
   find_package(Boost 1.58 REQUIRED COMPONENTS system thread python-py35)
endif()

# Find python3
find_package(PythonInterp 3 REQUIRED)
find_package(PythonLibs 3 REQUIRED)

# Optional EPICS V3
if(DEFINED ENV{EPICS_BASE})
   set(DO_EPICS_V3 1)
   set(EPICS_INCLUDES ${EPICS_BASE}/include ${EPICS_BASE}/include/compiler/gcc ${EPICS_BASE}/include/os/Linux)
   set(EPICS_LIB_DIR  ${EPICS_BASE}/lib/rhel6-x86_64/)
   set(EPICS_LIBS cas ca Com gdd)
else()
   set(DO_EPICS_V3 0)
endif()

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
include_directories(${EPICS_INCLUDES})

# Create rogue core library
add_library(rogue-core SHARED "")

# Find sources
add_subdirectory(src/rogue)

# Set output to TOP/lib
set_target_properties(rogue-core PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/lib)

# Link to boost, python and bzip
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${PYTHON_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${EPICS_LIBS})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC bz2)

# Create rogue python library
add_library(rogue SHARED "")

# Find sources
add_subdirectory(src)

# Set output to TOP/python, remove lib prefix
set_target_properties(rogue PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/python)
set_target_properties(rogue PROPERTIES PREFIX "")

# Link to rogue
TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC rogue-core)

