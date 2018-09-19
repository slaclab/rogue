# ----------------------------------------------------------------------------
# Title      : ROGUE CMAKE Control
# ----------------------------------------------------------------------------
# File       : src/rogue/protocols/rssi/CMakeLists.txt
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

target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Application.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Client.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Controller.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Header.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Server.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/Transport.cpp")

if (DO_PYTHON)
   target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/module.cpp")
endif()
