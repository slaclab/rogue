# ----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
# ----------------------------------------------------------------------------
# This file is part of the rogue software package. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software package, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/AxiMemMap.cpp")
target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/AxiStreamDma.cpp")

if (NOT NO_PYTHON)
   target_sources(rogue-core PRIVATE "${CMAKE_CURRENT_LIST_DIR}/module.cpp")
endif()
