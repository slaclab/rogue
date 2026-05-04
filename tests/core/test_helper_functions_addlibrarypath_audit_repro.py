#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   addLibraryPath() in _HelperFunctions.py contains a duplicated
#   `if base == '': base = '.'` block (lines 74-79): the same guard appears
#   twice back-to-back with identical surrounding comments.  On HEAD the
#   string `if base == '':` appears twice in lines 70-90, so the assertion
#   below FAILS.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import inspect

import pyrogue._HelperFunctions as hf


def test_addlibrarypath_no_duplicate_blocks():
    """addLibraryPath has a duplicated `if base == '':` block."""
    src_lines = inspect.getsource(hf.addLibraryPath).splitlines()

    # Count occurrences of the guarded assignment within the function source.
    count = sum(
        1 for line in src_lines
        if "if base == '':" in line
    )

    assert count <= 1, (
        "addLibraryPath has duplicated `if base == '':` block "
        "(copy-paste artifact); found " + str(count) + " occurrences — expected at most 1"
    )
