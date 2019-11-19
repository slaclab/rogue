# ----------------------------------------------------------------------------
# Title      : ROGUE CMAKE Control
# ----------------------------------------------------------------------------
# File       : src/rogue/hardware/CMakeLists.txt
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

add_subdirectory("pgp")
add_subdirectory("axi")

target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/MemMap.cpp")

if (NOT NO_PYTHON)
   target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/module.cpp")
endif()
