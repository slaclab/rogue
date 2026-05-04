#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   _RegInterfParser.parse() calls ZipFile.extractall() at line 74-75 without
#   sanitising zip entry names against path traversal (zip-slip).  The fix
#   requires iterating over namelist() and rejecting entries whose resolved
#   path escapes the destination directory, OR passing filter='data' (Python
#   3.12+).  On HEAD neither mitigation is present → assertion FAILS.
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

import pyrogue.utilities.hls._RegInterfParser as parser_mod


def test_hls_parser_zip_slip_audit():
    """_RegInterfParser.parse() uses extractall without zip-slip sanitisation."""
    src = inspect.getsource(parser_mod.parse)

    # A safe implementation sanitises zip entry paths before extraction:
    # either by filtering out traversal sequences or by passing filter='data'
    # (Python 3.12+).  Assert at least one mitigation is present.
    has_mitigation = (
        "filter=" in src             # Python 3.12+ filter='data'
        or "os.path.realpath" in src  # manual path canonicalisation
        or "os.path.abspath" in src   # manual path canonicalisation
        or ".startswith(" in src      # prefix check after realpath
    )

    assert has_mitigation, (
        "_RegInterfParser.parse() calls ZipFile.extractall() "
        "at line 74-75 without any zip-slip sanitisation; a zip entry "
        "containing path-traversal sequences (e.g.../../evil) can write "
        "files outside the extraction directory"
    )
