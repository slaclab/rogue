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
   link_directories($ENV{CONDA_PREFIX}/lib)
endif()

# Check cmake version
cmake_minimum_required(VERSION 3.5)
include(InstallRequiredSystemLibraries)

# Project name
project (rogue)

# C/C++
enable_language(CXX)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x -Wno-deprecated")

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
   if(DEFINED ENV{EPICS_HOST_ARCH})
       set(EPICSV3_ARCH      $ENV{EPICS_HOST_ARCH})
   else()
       execute_process(COMMAND ${EPICSV3_BASE_DIR}/startup/EpicsHostArch 
                       OUTPUT_VARIABLE EPICSV3_ARCH OUTPUT_STRIP_TRAILING_WHITESPACE)
       string(REGEX REPLACE "\n$" "" EPICSV3_ARCH "${EPICSV3_ARCH}")
   endif()
   set(EPICSV3_LIB_DIR   ${EPICSV3_BASE_DIR}/lib/${EPICSV3_ARCH} )
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
# Generate version with GIT
#####################################

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
# Setup Type and Directories
#####################################

# Default install type
if ( NOT ROGUE_INSTALL ) 
   set (ROGUE_INSTALL "local")
endif()

# Default Install directory
if (${ROGUE_INSTALL} STREQUAL "local")
   set (ROGUE_DIR ${PROJECT_SOURCE_DIR})
elseif (NOT ROGUE_DIR) 
   if (${ROGUE_INSTALL} STREQUAL "custom")
      set (ROGUE_DIR "$ENV{CONDA_PREFIX}/${CMAKE_INSTALL_PREFIX}/rogue")
   else()
      set (ROGUE_DIR "$ENV{CONDA_PREFIX}/${CMAKE_INSTALL_PREFIX}")
   endif()
endif()

#####################################
# Setup build, core library
#####################################

# Configuration File
configure_file (
   ${PROJECT_SOURCE_DIR}/templates/RogueConfig.h.in
   ${PROJECT_BINARY_DIR}/RogueConfig.h
)

# Add include directories
include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(${PROJECT_BINARY_DIR})
include_directories(${Boost_INCLUDE_DIRS})
include_directories(${PYTHON_INCLUDE_DIRS})
include_directories(${EPICSV3_INCLUDES})

SET(CMAKE_SHARED_LIBRARY_SUFFIX ".so")

# Create rogue core library
add_library(rogue-core SHARED "")

# Find rogue core sources
add_subdirectory(src/rogue)

# Link rogue core to boost, python and bzip
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${PYTHON_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${EPICSV3_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC bz2)

# Set output library names
set_target_properties(rogue-core PROPERTIES VERSION ${ROGUE_VERSION} SOVERSION ${ROGUE_SOVER})

#####################################
# Setup build, python library
#####################################

if (DO_PYTHON)

   # Create rogue python library
   add_library(rogue SHARED "")

   # Find python package sources
   add_subdirectory(src)

   # Set output to TOP/python, remove lib prefix
   set_target_properties(rogue PROPERTIES PREFIX "")

   # Link to rogue core
   TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC rogue-core)

else()
   add_definitions( -DNO_PYTHON )
endif()

#########################################
# Configuration & Setup Script Generation
#########################################

# Setup configuration file
set(CONF_INCLUDE_DIRS ${ROGUE_DIR}/include
                      ${Boost_INCLUDE_DIRS}
                      ${PYTHON_INCLUDE_DIRS}
                      ${EPICSV3_INCLUDES})
 
set(CONF_LIBRARIES    ${ROGUE_DIR}/lib/librogue-core.so.${ROGUE_SOVER}
                      ${Boost_LIBRARIES}
                      ${PYTHON_LIBRARIES}
                      ${EPICSV3_LIBRARIES}
                      LINK_PUBLIC bz2)

# Create the config file
configure_file(${PROJECT_SOURCE_DIR}/templates/RogueConfig.cmake.in 
               ${PROJECT_BINARY_DIR}/RogueConfig.cmake @ONLY)

# Create the setup files
configure_file(${PROJECT_SOURCE_DIR}/templates/setup_rogue.csh.in
               ${PROJECT_BINARY_DIR}/setup_rogue.csh @ONLY)
configure_file(${PROJECT_SOURCE_DIR}/templates/setup_rogue.sh.in
               ${PROJECT_BINARY_DIR}/setup_rogue.sh @ONLY)

# Python distutils setup script
configure_file ( ${PROJECT_SOURCE_DIR}/templates/setup.py.in
                 ${PROJECT_BINARY_DIR}/setup.py
)

#####################################
# Install Setup
#####################################

# Always install core libraries and config files
install(TARGETS rogue-core LIBRARY DESTINATION ${ROGUE_DIR}/lib)
install(FILES   ${PROJECT_BINARY_DIR}/RogueConfig.cmake DESTINATION ${ROGUE_DIR}/lib)

# Copy setup files for local or custom
if ((${ROGUE_INSTALL} STREQUAL "custom") OR (${ROGUE_INSTALL} STREQUAL "local"))
   install(FILES ${PROJECT_BINARY_DIR}/setup_rogue.sh ${PROJECT_BINARY_DIR}/setup_rogue.csh DESTINATION ${ROGUE_DIR})
endif()

# Install header files for custom or system
if ((${ROGUE_INSTALL} STREQUAL "custom") OR (${ROGUE_INSTALL} STREQUAL "system"))
   install(DIRECTORY ${PROJECT_SOURCE_DIR}/include/rogue
           DESTINATION ${ROGUE_DIR}/include FILES_MATCHING PATTERN "*.h")
endif()

# Python file install
if (DO_PYTHON)

   # Install python files directly for custom install
   if (${ROGUE_INSTALL} STREQUAL "custom")
      install(DIRECTORY ${PROJECT_SOURCE_DIR}/python/pyrogue DESTINATION ${ROGUE_DIR}/python FILES_MATCHING PATTERN "*.py")

   # Use distutils to isntall python for system install
   elseif (${ROGUE_INSTALL} STREQUAL "system")
      install(CODE "execute_process(COMMAND python3 ${PROJECT_BINARY_DIR}/setup.py install)")
   endif()

   # Copy library for custom or local, do byte compiles
   if ((${ROGUE_INSTALL} STREQUAL "custom") OR (${ROGUE_INSTALL} STREQUAL "local"))
      install(TARGETS rogue LIBRARY DESTINATION ${ROGUE_DIR}/python)
      install(CODE "execute_process(COMMAND python3 -m compileall ${ROGUE_DIR}/python)")
   endif()   

endif()

#####################################
# Print status
#####################################

message("")
message("----------------------------------------------------------------------")
message("-- Rogue Version: ${ROGUE_VERSION}")
message("")
message("-- Install Type: ${ROGUE_INSTALL}")
message("")
message("-- Install Path: ${ROGUE_DIR}")
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

