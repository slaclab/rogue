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

rogue_add_cpp_test(rogue-cpp-rocev2
   SOURCES
      test_rocev2.cpp
   LABELS
      cpp-rocev2
      requires-python
   LIBRARIES
      ibverbs
)

# Isolated in its own binary: on a buggy (unpatched) build this test provokes a
# genuine use-after-free (SIGSEGV) at the teardown read, so keeping it separate
# means a regression here cannot abort the other rocev2 cpp cases.
rogue_add_cpp_test(rogue-cpp-rocev2-teardown
   SOURCES
      test_rocev2_teardown.cpp
   LABELS
      cpp-rocev2
      requires-python
   LIBRARIES
      ibverbs
)
