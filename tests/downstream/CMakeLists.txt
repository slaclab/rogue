# ----------------------------------------------------------------------------
# Title      : Downstream find_package(Rogue) smoke fixture
# ----------------------------------------------------------------------------
# Description:
# Standalone CMake project that consumes an INSTALLED rogue purely through
# find_package(Rogue) / RogueConfig.cmake. It is NOT part of the rogue build;
# the downstream_find_package_test CI job configures it separately against an
# installed rogue to prove templates/RogueConfig.cmake.in works for consumers.
#
# Two build styles, selected by -DDOWNSTREAM_NO_PYTHON:
#   OFF (default): build BitInverter.so, a boost.python loadable module (the
#                  common downstream use case), loaded by verify_bit_inversion.py.
#   ON           : build bit_inverter_check, a standalone C++ executable that
#                  asserts the inversion in-process (no Python/Boost).
#
# This mirrors the documented custom-module CMakeLists.txt
# (docs/src/custom_module/makefile.rst); keep the two consistent.
# ----------------------------------------------------------------------------

# Add support for building in conda environment
if (DEFINED ENV{CONDA_PREFIX})
   set(CMAKE_PREFIX_PATH "$ENV{CONDA_PREFIX}")
   link_directories($ENV{CONDA_PREFIX}/lib)
endif()

cmake_minimum_required(VERSION 3.15)
include(InstallRequiredSystemLibraries)

project(rogue_downstream_fixture CXX)

option(DOWNSTREAM_NO_PYTHON "Build the standalone C++ executable instead of the Python module" OFF)

# C/C++
enable_language(CXX)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wno-deprecated")
add_definitions(-D__STDC_FORMAT_MACROS)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_SKIP_BUILD_RPATH TRUE)
set(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH FALSE)

#####################################
# Find Rogue & Support Libraries
#####################################
# ROGUE_DIR is exported by setup_rogue.sh; Rogue_DIR points cmake at the
# directory that contains the installed RogueConfig.cmake.
if (DEFINED ENV{ROGUE_DIR})
   set(Rogue_DIR $ENV{ROGUE_DIR}/lib)
else()
   set(Rogue_DIR ${CMAKE_PREFIX_PATH}/lib)
endif()
find_package(Rogue REQUIRED)

#####################################
# Build
#####################################
include_directories(${ROGUE_INCLUDE_DIRS})

if (DOWNSTREAM_NO_PYTHON)
   # Standalone C++ check: rogue built with -DNO_PYTHON=1 -DSTATIC_LIB=1.
   add_definitions(-DNO_PYTHON)
   add_executable(bit_inverter_check src/BitInverter.cpp)
   target_link_libraries(bit_inverter_check LINK_PUBLIC ${ROGUE_LIBRARIES})
else()
   # Python-loadable module: BitInverter.so in the build dir for PYTHONPATH.
   add_library(BitInverter SHARED src/BitInverter.cpp)
   set_target_properties(BitInverter PROPERTIES PREFIX "" SUFFIX ".so")
   target_link_libraries(BitInverter LINK_PUBLIC ${ROGUE_LIBRARIES})
endif()
