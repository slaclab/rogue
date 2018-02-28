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

project(rogue)

# Create rogue library
add_library(rogue SHARED "")

# Set output to TOP/lib
set_target_properties(rogue PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/../../lib")

# Link to boost, python and bzip
TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC ${PYTHON_LIBRARIES})
TARGET_LINK_LIBRARIES(rogue LINK_PUBLIC "bz2")

# Add sub directories
add_subdirectory("hardware")
add_subdirectory("interfaces")
add_subdirectory("protocols")
add_subdirectory("utilities")

# Local sources
file(GLOB rogue_SRC "*.cpp")
target_sources(rogue PUBLIC ${rogue_SRC})

