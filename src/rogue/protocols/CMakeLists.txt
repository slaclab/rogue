# ----------------------------------------------------------------------------
# Title      : ROGUE CMAKE Control
# ----------------------------------------------------------------------------
# File       : src/rogue/protocols/CMakeLists.txt
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

add_subdirectory("packetizer")
add_subdirectory("rssi")
add_subdirectory("srp")
add_subdirectory("udp")

if (DO_EPICS_V3)
   add_subdirectory("epicsV3")
endif()

if (DO_PYTHON)
   target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/module.cpp")
endif()
