# ----------------------------------------------------------------------------
# Title      : ROGUE CMAKE Control
# ----------------------------------------------------------------------------
# This file is part of the rogue software package. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software package, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------
# See notes for compiling on macros under anaconda:
#    https://conda.io/docs/user-guide/tasks/build-packages/compiler-tools.html

# Add support for building in conda environment
if (DEFINED ENV{CONDA_PREFIX})
   set(CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
   link_directories($ENV{CONDA_PREFIX}/lib)
endif()

# Check cmake version
cmake_minimum_required(VERSION 3.5)
include(InstallRequiredSystemLibraries)

# Set default release type
if (NOT EXISTS ${CMAKE_BINARY_DIR}/CMakeCache.txt)
  if (NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING "" FORCE)
  endif()
endif()

# Project name
project (rogue)

# C/C++
enable_language(CXX)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -Wno-deprecated")
add_definitions(-D__STDC_FORMAT_MACROS)

SET(CMAKE_SKIP_BUILD_RPATH TRUE)
SET(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)
SET(CMAKE_INSTALL_RPATH_USE_LINK_PATH FALSE)

#####################################
# Boost + Python
#####################################
if ( NOT NO_PYTHON )
   find_package(PythonInterp 3 QUIET REQUIRED)
   find_package(PythonLibs 3 QUIET REQUIRED)

   # Find Numpy
   execute_process(
      COMMAND python3 -c "import numpy; print(numpy.get_include(), end='')"
      RESULT_VARIABLE Python3_NumPy_RESULT
      OUTPUT_VARIABLE Python3_NumPy_INCLUDE_DIRS
      ERROR_QUIET
      OUTPUT_STRIP_TRAILING_WHITESPACE)

   if (Python3_NumPy_RESULT)
      message("")
      message(FATAL_ERROR "Failed to find numpy includes!")
   endif()

   set(Boost_USE_MULTITHREADED ON)
   set(Boost_NO_BOOST_CMAKE ON)

   # Hint for boost on anaconda
   if (DEFINED ENV{CONDA_PREFIX})
      set(BOOST_ROOT $ENV{CONDA_PREFIX})

   # SLAC AFS custom path
   elseif (DEFINED ENV{BOOST_PATH})
      set(BOOST_ROOT $ENV{BOOST_PATH})
   endif()

   # libboost_python3.7 style libraries
   message("Looking for libboost_python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}")
   FIND_PACKAGE(Boost 1.58 QUIET COMPONENTS python${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR})

   # libboost_python3 style libraries
   if (NOT Boost_FOUND)
      message("Looking for libboost_python${PYTHON_VERSION_MAJOR}")
      FIND_PACKAGE(Boost 1.58 QUIET COMPONENTS python${PYTHON_VERSION_MAJOR})
   endif()

   # libboost_python style libraries
   if (NOT Boost_FOUND)
      message("Looking for libboost_python")
      FIND_PACKAGE(Boost 1.58 QUIET COMPONENTS system thread python)
   endif()

   # libboost_python-py37 style libraries
   if (NOT Boost_FOUND)
      message("Looking for libboost_python-py${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}")
      FIND_PACKAGE(Boost 1.58 QUIET COMPONENTS python-py${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR})
   endif()

   # libboost_python3-py37 style libraries
   if (NOT Boost_FOUND)
      message("Looking for libboost_python3-py${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR}")
      FIND_PACKAGE(Boost 1.58 QUIET COMPONENTS python3-py${PYTHON_VERSION_MAJOR}${PYTHON_VERSION_MINOR})
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
# First try with cmake packages
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

      # Get the base directory
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
   set(EPICS_BASE_DIR $ENV{EPICS_BASE})
   if(DEFINED ENV{EPICS_HOST_ARCH})
       set(EPICS_ARCH $ENV{EPICS_HOST_ARCH})
   else()
       execute_process(COMMAND ${EPICS_BASE_DIR}/startup/EpicsHostArch
                       OUTPUT_VARIABLE EPICS_ARCH OUTPUT_STRIP_TRAILING_WHITESPACE)
       string(REGEX REPLACE "\n$" "" EPICS_ARCH "${EPICS_ARCH}")
   endif()

   # PCAS is part of epics before version 4
   if(EPICS_PCAS_ROOT)
      set(EPICS_PCAS_DIR ${EPICS_PCAS_ROOT})
   elseif(DEFINED ENV{EPICS_PCAS_ROOT})
      set(EPICS_PCAS_DIR $ENV{EPICS_PCAS_ROOT})
   else()
      set(EPICS_PCAS_DIR $ENV{EPICS_BASE})
   endif()

   # See if we can find the pcas header, may not exist if epics 7 without pcas is installed
   find_path(E3_TEST_INCLUDE_DIR NAMES casdef.h PATHS ${EPICS_PCAS_DIR}/include)
   if (NOT E3_TEST_INCLUDE_DIR)
      set(DO_EPICS_V3 0)
   elseif(APPLE)

      set(EPICS_INCLUDES    ${EPICS_PCAS_DIR}/include
                            ${EPICS_BASE_DIR}/include
                            ${EPICS_BASE_DIR}/include/compiler/clang
                            ${EPICS_BASE_DIR}/include/os/Darwin)

      set(EPICS_LIBRARIES   ${EPICS_PCAS_DIR}/lib/${EPICS_ARCH}/libcas.dylib
                            ${EPICS_PCAS_DIR}/lib/${EPICS_ARCH}/libgdd.dylib
                            ${EPICS_BASE_DIR}/lib/${EPICS_ARCH}/libca.dylib
                            ${EPICS_BASE_DIR}/lib/${EPICS_ARCH}/libCom.dylib )
   else()

      set(EPICS_INCLUDES    ${EPICS_PCAS_DIR}/include
                            ${EPICS_BASE_DIR}/include
                            ${EPICS_BASE_DIR}/include/compiler/gcc
                            ${EPICS_BASE_DIR}/include/os/Linux)

      set(EPICS_LIBRARIES   ${EPICS_PCAS_DIR}/lib/${EPICS_ARCH}/libcas.so
                            ${EPICS_PCAS_DIR}/lib/${EPICS_ARCH}/libgdd.so
                            ${EPICS_BASE_DIR}/lib/${EPICS_ARCH}/libca.so
                            ${EPICS_BASE_DIR}/lib/${EPICS_ARCH}/libCom.so )
   endif()

else()
   set(DO_EPICS_V3 0)
endif()


##########################################################
# Generate version with GIT If Not Passed As -DVERSION
##########################################################
if ( NOT ROGUE_VERSION )

   # Set version from git tag
   find_package(Git QUIET)
   if (GIT_FOUND)
      execute_process (
         COMMAND ${GIT_EXECUTABLE} --git-dir=${CMAKE_SOURCE_DIR}/.git --work-tree=${CMAKE_SOURCE_DIR} describe --tags --dirty
         OUTPUT_VARIABLE ROGUE_VERSION
         OUTPUT_STRIP_TRAILING_WHITESPACE)
   else()
      message("")
      message(FATAL_ERROR "Git is required to build rogue!")
   endif()
endif()

string(REGEX MATCH "^v([0-9]+)\\.([0-9]+)" ROGUE_SOVER ${ROGUE_VERSION})

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

if ( NOT CMAKE_INSTALL_LIBDIR )
   set (CMAKE_INSTALL_LIBDIR "${ROGUE_DIR}/lib")
endif()

if ( NOT CMAKE_INSTALL_INCLUDEDIR )
   set (CMAKE_INSTALL_INCLUDEDIR "${ROGUE_DIR}/include")
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
include_directories(system ${Python3_NumPy_INCLUDE_DIRS})
include_directories(system ${ZeroMQ_INCLUDE_DIR})
include_directories(system ${BZIP2_INCLUDE_DIR})
include_directories(system ${EPICS_INCLUDES})

if (APPLE)
   SET(CMAKE_SHARED_LIBRARY_SUFFIX ".dylib")
else()
   SET(CMAKE_SHARED_LIBRARY_SUFFIX ".so")
endif()

# Create rogue core library
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
add_library(rogue-core OBJECT "")

# Find rogue core sources
add_subdirectory(src/rogue)

# Always build shared library
add_library(rogue-core-shared SHARED $<TARGET_OBJECTS:rogue-core> "")
set_target_properties(rogue-core-shared PROPERTIES OUTPUT_NAME librogue-core)
set_target_properties(rogue-core-shared PROPERTIES PREFIX "" SUFFIX ".so")
set_target_properties(rogue-core-shared PROPERTIES VERSION ${ROGUE_VERSION} SOVERSION ${ROGUE_SOVER})

TARGET_LINK_LIBRARIES(rogue-core-shared PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core-shared PUBLIC ${ZeroMQ_LIBRARY})
TARGET_LINK_LIBRARIES(rogue-core-shared PUBLIC ${EPICS_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue-core-shared PUBLIC ${BZIP2_LIBRARIES})

# Do not link directly against python in mac os
if (APPLE)
   set_target_properties(rogue-core-shared PROPERTIES LINK_FLAGS "-undefined dynamic_lookup")
else()
   TARGET_LINK_LIBRARIES(rogue-core-shared PUBLIC ${PYTHON_LIBRARIES})
   TARGET_LINK_LIBRARIES(rogue-core-shared PUBLIC rt)
endif()

if(STATIC_LIB)
    add_library(rogue-core-static STATIC $<TARGET_OBJECTS:rogue-core> "")
    set_target_properties(rogue-core-static PROPERTIES OUTPUT_NAME librogue-core)
    set_target_properties(rogue-core-static PROPERTIES PREFIX "" SUFFIX ".a")

    # Link rogue core to boost, python and bzip
    TARGET_LINK_LIBRARIES(rogue-core-static PUBLIC ${Boost_LIBRARIES})
    TARGET_LINK_LIBRARIES(rogue-core-static PUBLIC ${ZeroMQ_LIBRARY})
    TARGET_LINK_LIBRARIES(rogue-core-static PUBLIC ${EPICS_LIBRARIES})
    TARGET_LINK_LIBRARIES(rogue-core-static PUBLIC ${BZIP2_LIBRARIES})
    TARGET_LINK_LIBRARIES(rogue-core-static PUBLIC ${PYTHON_LIBRARIES})
    TARGET_LINK_LIBRARIES(rogue-core-static PUBLIC rt)
endif()


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
   TARGET_LINK_LIBRARIES(rogue PUBLIC rogue-core-shared)

else()
   add_definitions( -DNO_PYTHON )
endif()


#########################################
# Configuration & Setup Script Generation
#########################################
set(CONF_INCLUDE_DIRS ${CMAKE_INSTALL_INCLUDEDIR})

# Setup configuration file
if ((${ROGUE_INSTALL} STREQUAL "system") OR (${ROGUE_INSTALL} STREQUAL "conda"))
   set(CONF_LIBRARIES PUBLIC rogue-core)
else()
   if (APPLE)
      set(CONF_LIBRARIES ${CMAKE_INSTALL_LIBDIR}/librogue-core.${ROGUE_SOVER}.dylib)
   else()
      set(CONF_LIBRARIES ${CMAKE_INSTALL_LIBDIR}/librogue-core.so.${ROGUE_SOVER})
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
if (STATIC_LIB)
   install(TARGETS rogue-core-static LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR} ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
endif()

install(TARGETS rogue-core-shared LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR} ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})

install(FILES ${PROJECT_BINARY_DIR}/RogueConfig.cmake DESTINATION ${CMAKE_INSTALL_LIBDIR})

# Copy setup files for local or custom
if ((${ROGUE_INSTALL} STREQUAL "custom") OR (${ROGUE_INSTALL} STREQUAL "local"))
   install(FILES ${PROJECT_BINARY_DIR}/setup_rogue.sh ${PROJECT_BINARY_DIR}/setup_rogue.csh DESTINATION ${ROGUE_DIR})
endif()

# Install header files for non local installs
if (NOT (${ROGUE_INSTALL} STREQUAL "local"))
   install(DIRECTORY ${PROJECT_SOURCE_DIR}/include/rogue DESTINATION ${CMAKE_INSTALL_INCLUDEDIR} FILES_MATCHING PATTERN "*.h")
endif()

# Conda activate and deactivate functions
if ((${ROGUE_INSTALL} STREQUAL "conda"))
   install(CODE "execute_process(COMMAND scp ${PROJECT_SOURCE_DIR}/templates/activate-rogue.sh
                                             ${ROGUE_DIR}/etc/conda/activate.d/rogue.sh)")
   install(CODE "execute_process(COMMAND scp ${PROJECT_SOURCE_DIR}/templates/deactivate-rogue.sh
                                             ${ROGUE_DIR}/etc/conda/deactivate.d/rogue.sh)")
endif()

# Python file install
if (NOT NO_PYTHON)

   # Install python files directly for custom install
   if (${ROGUE_INSTALL} STREQUAL "custom")
      install(DIRECTORY ${PROJECT_SOURCE_DIR}/python/pyrogue DESTINATION ${ROGUE_DIR}/python FILES_MATCHING PATTERN "*.py")
      install(TARGETS rogue LIBRARY DESTINATION ${ROGUE_DIR}/python)

   # Use setuptools with python3 for system
   elseif (${ROGUE_INSTALL} STREQUAL "system")
      install(CODE "execute_process(COMMAND python3 ${PROJECT_BINARY_DIR}/setup.py install)")

   # Use setuptools with python for anaconda
   elseif (${ROGUE_INSTALL} STREQUAL "conda")
      install(CODE "execute_process(COMMAND python
              ${PROJECT_BINARY_DIR}/setup.py install --prefix=${ROGUE_DIR})")
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
   message("-- Found boost: ${Boost_LIBRARIES}")
   message("")
   message("-- Found python: ${PYTHON_LIBRARIES}")
   message("")
   message("-- Found numpy: ${Python3_NumPy_INCLUDE_DIRS}")
endif()

message("")

if (DO_EPICS_V3)
   message("-- Found EPICS: ${EPICS_BASE_DIR}")
   message("")
   message("-- Found PCAS:  ${EPICS_PCAS_DIR}")
else()
   message("-- EPICS V3 not included!")
endif()

message("")
message("-- Found ZeroMq: ${ZeroMQ_INCLUDE_DIR}")
message("")
message("-- Found Bzip2: ${BZIP2_INCLUDE_DIR}")
message("")
message("-- Link dynamic rogue library!")

if (STATIC_LIB)
   message("-- Link static rogue library!")
endif()

message("----------------------------------------------------------------------")
message("")

