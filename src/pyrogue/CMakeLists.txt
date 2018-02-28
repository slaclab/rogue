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

project(pyrogue)

# Create rogue library
add_library(pyrogue SHARED "")

# Set output to TOP/python
set_target_properties(pyrogue PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${PROJECT_SOURCE_DIR}/../../python")

# Link to rogue library
TARGET_LINK_LIBRARIES(pyrogue LINK_PUBLIC ${Boost_LIBRARIES})
TARGET_LINK_LIBRARIES(pyrogue LINK_PUBLIC ${PYTHON_LIBRARIES})
TARGET_LINK_LIBRARIES(pyrogue LINK_PUBLIC rogue)

# Local sources
file(GLOB pyrogue_SRC "*.cpp")
target_sources(pyrogue PUBLIC ${pyrogue_SRC})

