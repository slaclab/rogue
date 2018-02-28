# ----------------------------------------------------------------------------
# Title      : ROGUE CMAKE Control
# ----------------------------------------------------------------------------
# File       : src/rogue/CMakeLists.txt
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

# Add sub directories
add_subdirectory("hardware")
add_subdirectory("interfaces")
add_subdirectory("protocols")
add_subdirectory("utilities")

# Local sources
file(GLOB rogue_SRC "*.cpp")
target_sources(rogue PRIVATE ${rogue_SRC})
