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
# See notes for compiling on macos under anaconda:
#    https://conda.io/docs/user-guide/tasks/build-packages/compiler-tools.html

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
#set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x -Wno-deprecated")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -Wno-deprecated")
add_definitions(-D__STDC_FORMAT_MACROS)

#####################################
# Boost + Python
#####################################
if ( NOT NO_PYTHON ) 
   find_package(PythonInterp 3.6 QUIET REQUIRED)
   find_package(PythonLibs 3.6 QUIET REQUIRED)

   set(Boost_USE_MULTITHREADED ON)

   # Boost may need help on SLAC machines
   set(BOOST_ROOT:PATHNAME $ENV{BOOST_PATH})

   # First try standard suffix for boost
   find_package(Boost 1.58 QUIET COMPONENTS system thread python3)

   # Next try Debian/Ubuntu suffix for boost
   if (NOT Boost_FOUND)
      find_package(Boost 1.58 QUIET COMPONENTS system thread python-py36)
   endif()

   # Next try Mac with homebrew boost/python36
   if (NOT Boost_FOUND)
      find_package(Boost 1.58 QUIET COMPONENTS system thread python36)
   endif()

   # Next try anaconda with python 3.7
   if (NOT Boost_FOUND)
      find_package(Boost 1.58 QUIET COMPONENTS system thread python37)
   endif()

   # Nothing worked
   if (NOT Boost_FOUND)
      message("")
      message(FATAL_ERROR "Failed to find boost libraries!")
   endif()
else()
   add_definitions( -DNO_PYTHON )
endif()

#####################################
# BZIP2
#####################################
   find_package(BZip2 QUIET REQUIRED)

#####################################
# ZeroMQ
#####################################
   # First try with Cmake packages
   find_package(ZeroMQ QUIET)

   # ZeroMQ does not always support cmake, use brute force
   if (NOT ZeroMQ_FOUND)
      
      # Convert LD_LIBRARY PATH for search
      if(DEFINED ENV{LD_LIBRARY_PATH})
         string(REPLACE ":" ";" HINT_PATHS $ENV{LD_LIBRARY_PATH})
      else()
         set(HINT_PATHS, "")
      endif()

      # See if zmq library is in LD_LIBRARY_PATH
      find_library(ZeroMQ_LIBRARY 
                   NAMES zmq 
                   PATHS ${HINT_PATHS})

      # Found it
      if (ZeroMQ_LIBRARY) 

         # Get the base diretory
         get_filename_component(ZMQ_LIBDIR ${ZeroMQ_LIBRARY} DIRECTORY)

         # See if we can find the header in a relative path
         find_path(ZeroMQ_INCLUDE_DIR
                 NAMES zmq.h
                 PATHS ${ZMQ_LIBDIR}/../include
                 )
         if (NOT ZeroMQ_INCLUDE_DIR)
            message("")
            message(FATAL_ERROR "Failed to find ZeroMQ_INCLUDE_DIR!")
         endif()
      else()
         # Failed to find it
         message("")
         message(FATAL_ERROR "Failed to find zeroMQ!")
      endif()
   endif()

#####################################
# EPICS V3
#####################################
if((NOT NO_PYTHON) AND (NOT NO_EPICS) AND DEFINED ENV{EPICS_BASE})
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

   if(APPLE)

      if(EPICS_PCAS_ROOT)
         set(EPICSV3_INCLUDES  ${EPICS_PCAS_ROOT}/include
                               ${EPICSV3_BASE_DIR}/include
                               ${EPICSV3_BASE_DIR}/include/compiler/gcc 
                               ${EPICSV3_BASE_DIR}/include/os/Darwin)

         set(EPICSV3_LIBRARIES ${EPICS_PCAS_ROOT}/lib/${EPICSV3_ARCH}/libcas.dylib 
                               ${EPICS_PCAS_ROOT}/lib/${EPICSV3_ARCH}/libgdd.dylib
                               ${EPICSV3_LIB_DIR}/libca.dylib 
                               ${EPICSV3_LIB_DIR}/libCom.dylib )
      else()
         set(EPICSV3_INCLUDES  ${EPICSV3_BASE_DIR}/include
                               ${EPICSV3_BASE_DIR}/include/compiler/gcc 
                               ${EPICSV3_BASE_DIR}/include/os/Darwin)

         set(EPICSV3_LIBRARIES ${EPICSV3_LIB_DIR}/libcas.dylib 
                               ${EPICSV3_LIB_DIR}/libca.dylib
                               ${EPICSV3_LIB_DIR}/libCom.dylib
                               ${EPICSV3_LIB_DIR}/libgdd.dylib )
      endif()
   else()

      if(EPICS_PCAS_ROOT)
         set(EPICSV3_INCLUDES  ${EPICS_PCAS_ROOT}/include
                               ${EPICSV3_BASE_DIR}/include
                               ${EPICSV3_BASE_DIR}/include/compiler/gcc 
                               ${EPICSV3_BASE_DIR}/include/os/Linux)

         set(EPICSV3_LIBRARIES ${EPICS_PCAS_ROOT}/lib/${EPICSV3_ARCH}/libcas.so 
                               ${EPICS_PCAS_ROOT}/lib/${EPICSV3_ARCH}/libgdd.so
                               ${EPICSV3_LIB_DIR}/libca.so 
                               ${EPICSV3_LIB_DIR}/libCom.so )
      else()
         set(EPICSV3_INCLUDES  ${EPICSV3_BASE_DIR}/include
                               ${EPICSV3_BASE_DIR}/include/compiler/gcc 
                               ${EPICSV3_BASE_DIR}/include/os/Linux)

         set(EPICSV3_LIBRARIES ${EPICSV3_LIB_DIR}/libcas.so 
                               ${EPICSV3_LIB_DIR}/libca.so
                               ${EPICSV3_LIB_DIR}/libCom.so
                               ${EPICSV3_LIB_DIR}/libgdd.so )
      endif()
   endif()
else()
   set(DO_EPICS_V3 0)
endif()

#####################################
# Generate version with GIT
#####################################

# Set version from git tag
find_package(Git QUIET)
if (GIT_FOUND)
   execute_process (
      COMMAND ${GIT_EXECUTABLE} --git-dir=${CMAKE_SOURCE_DIR}/.git  describe --tags --dirty
      OUTPUT_VARIABLE ROGUE_VERSION
      OUTPUT_STRIP_TRAILING_WHITESPACE)

   string(REGEX MATCH "^v([0-9]+)\\.([0-9]+)" ROGUE_SOVER ${ROGUE_VERSION})
else()
   message("")
   message(FATAL_ERROR "Git is required to build rogue!")
endif()

#####################################
# Setup Type and Directories
#####################################

# Default install type
if ( NOT ROGUE_INSTALL ) 
   if (DEFINED ENV{CONDA_PREFIX})
      set (ROGUE_INSTALL "conda")
   else()
      set (ROGUE_INSTALL "local")
   endif()
endif()

# Default Install directory
if (${ROGUE_INSTALL} STREQUAL "local")
   set (ROGUE_DIR ${PROJECT_SOURCE_DIR})
elseif (NOT ROGUE_DIR) 
   if (${ROGUE_INSTALL} STREQUAL "custom")
      set (ROGUE_DIR "$ENV{CONDA_PREFIX}/${CMAKE_INSTALL_PREFIX}/rogue")
   elseif (${ROGUE_INSTALL} STREQUAL "conda")
      set (ROGUE_DIR "$ENV{CONDA_PREFIX}")
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
include_directories(system ${Boost_INCLUDE_DIRS})
include_directories(system ${PYTHON_INCLUDE_DIRS})
include_directories(system ${ZeroMQ_INCLUDE_DIR})
include_directories(system ${BZIP2_INCLUDE_DIR})
include_directories(system ${EPICSV3_INCLUDES})

if (APPLE)
   SET(CMAKE_SHARED_LIBRARY_SUFFIX ".dylib")
else()
   SET(CMAKE_SHARED_LIBRARY_SUFFIX ".so")
endif()

if(STATIC_LIB) 
set(LINK_MODE STATIC)
else()
set(LINK_MODE SHARED)
endif()

# Create rogue core library
add_library(rogue-core ${LINK_MODE} "")

# Find rogue core sources
add_subdirectory(src/rogue)

# Link rogue core to boost, python and bzip
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${ZeroMQ_LIBRARY})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${EPICSV3_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${BZIP2_LIBRARIES})

# Do not link directly against python in macos
if (APPLE)
   set_target_properties(rogue-core PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
else()
   TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC ${PYTHON_LIBRARIES})
   TARGET_LINK_LIBRARIES(rogue-core LINK_PUBLIC rt)
endif()

# Set output library names
set_target_properties(rogue-core PROPERTIES VERSION ${ROGUE_VERSION} SOVERSION ${ROGUE_SOVER})

#####################################
# Setup build, python library
#####################################
if (NOT NO_PYTHON)

   # Create rogue python library
   add_library(rogue SHARED "")

   # Find python package sources
   add_subdirectory(src)

   # Set output to TOP/python, remove lib prefix
   set_target_properties(rogue PROPERTIES PREFIX "" SUFFIX ".so")
   set_target_properties(rogue PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/python)

   if (APPLE)
      set_target_properties(rogue PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
   endif()

   # Link to rogue core
   TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC rogue-core)

else()
   add_definitions( -DNO_PYTHON )
endif()

#########################################
# Configuration & Setup Script Generation
#########################################
set(CONF_INCLUDE_DIRS ${ROGUE_DIR}/include)

# Setup configuration file
if ((${ROGUE_INSTALL} STREQUAL "system") OR (${ROGUE_INSTALL} STREQUAL "conda"))
   set(CONF_LIBRARIES LINK_PUBLIC rogue-core)
else()
   if (APPLE)
      set(CONF_LIBRARIES ${ROGUE_DIR}/lib/librogue-core.${ROGUE_SOVER}.dylib)
   else()
      set(CONF_LIBRARIES ${ROGUE_DIR}/lib/librogue-core.so.${ROGUE_SOVER})
   endif()
endif()

# Create the config file
configure_file(${PROJECT_SOURCE_DIR}/templates/RogueConfig.cmake.in 
               ${PROJECT_BINARY_DIR}/RogueConfig.cmake @ONLY)

# Create the setup files
configure_file(${PROJECT_SOURCE_DIR}/templates/setup_rogue.csh.in
               ${PROJECT_BINARY_DIR}/setup_rogue.csh @ONLY)
configure_file(${PROJECT_SOURCE_DIR}/templates/setup_rogue.sh.in
               ${PROJECT_BINARY_DIR}/setup_rogue.sh @ONLY)

# Create the python install script
configure_file(${PROJECT_SOURCE_DIR}/templates/setup.py.in
               ${PROJECT_BINARY_DIR}/setup.py)

#####################################
# Install Setup
#####################################

# Always install core libraries and config files
install(TARGETS rogue-core LIBRARY DESTINATION ${ROGUE_DIR}/lib ARCHIVE DESTINATION ${ROGUE_DIR}/lib)
install(FILES   ${PROJECT_BINARY_DIR}/RogueConfig.cmake DESTINATION ${ROGUE_DIR}/lib)

# Copy setup files for local or custom
if ((${ROGUE_INSTALL} STREQUAL "custom") OR (${ROGUE_INSTALL} STREQUAL "local"))
   install(FILES ${PROJECT_BINARY_DIR}/setup_rogue.sh ${PROJECT_BINARY_DIR}/setup_rogue.csh DESTINATION ${ROGUE_DIR})
endif()

# Install header files for non local installs
if (NOT (${ROGUE_INSTALL} STREQUAL "local"))
   install(DIRECTORY ${PROJECT_SOURCE_DIR}/include/rogue
           DESTINATION ${ROGUE_DIR}/include FILES_MATCHING PATTERN "*.h")
endif()

# Python file install
if (NOT NO_PYTHON)

   # Install python files directly for custom install
   if (${ROGUE_INSTALL} STREQUAL "custom")
      install(DIRECTORY ${PROJECT_SOURCE_DIR}/python/pyrogue DESTINATION ${ROGUE_DIR}/python FILES_MATCHING PATTERN "*.py")
      install(TARGETS rogue LIBRARY DESTINATION ${ROGUE_DIR}/python)

   # Use setuptools with python3 for system
   elseif (${ROGUE_INSTALL} STREQUAL "system")
      install(CODE "execute_process(COMMAND python3 ${PROJECT_SOURCE_DIR}/build/setup.py install)")
   
   # Use setuptools with python for anaconda
   elseif (${ROGUE_INSTALL} STREQUAL "conda")
      install(CODE "execute_process(COMMAND python 
              ${PROJECT_SOURCE_DIR}/build/setup.py install --prefix=${ROGUE_DIR})")
   endif()

   # Do byte compile for custom or local
   if ((${ROGUE_INSTALL} STREQUAL "custom") OR (${ROGUE_INSTALL} STREQUAL "local"))
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
message("-- Install Type: -DROGUE_INSTALL=${ROGUE_INSTALL}")
message("")
message("-- Install Path: -DROGUE_DIR=${ROGUE_DIR}")
message("")

if (NO_PYTHON)
   message("-- Compiling without boost & python!")
else()
message("-- Found boost: ${Boost_INCLUDE_DIRS}")
message("")
   message("-- Found python: ${PYTHON_LIBRARIES}")
endif()

message("")

if (DO_EPICS_V3)
   message("-- Found EPICS: ${EPICSV3_BASE_DIR}")
   if (EPICS_PCAS_ROOT)
      message("-- EPICS_PCAS_ROOT: ${EPICS_PCAS_ROOT}")
   endif()
else()
   message("-- EPICS V3 not included!")
endif()

message("")
message("-- Found ZeroMq: ${ZeroMQ_INCLUDE_DIR}")
message("")
message("-- Found Bzip2: ${BZIP2_INCLUDE_DIR}")
if (STATIC_LIB)
   message("-- Link static rogue library!")
endif()


message("----------------------------------------------------------------------")
message("")

