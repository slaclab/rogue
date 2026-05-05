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

    # A safe implementation must either:
    #   (a) Pass filter='data' to extractall (Python 3.12+), which rejects
    #       path-traversal entries inside the standard library; OR
    #   (b) Canonicalise each entry to an absolute path AND verify the
    #       canonical path is contained within the extraction directory.
    # A bare prefix check without canonicalisation is NOT sufficient: a
    # naive `path.startswith("/tmp/out")` lets `/tmp/outside` through.
    has_filter = "filter=" in src
    has_canonicalisation = (
        "os.path.realpath" in src or "os.path.abspath" in src
    )
    has_containment = (
        "os.path.commonpath" in src
        or "is_relative_to" in src
        or ".startswith(" in src   # safe only when paired with canonicalisation
    )
    has_mitigation = has_filter or (has_canonicalisation and has_containment)

    assert has_mitigation, (
        "_RegInterfParser.parse() calls ZipFile.extractall() without "
        "zip-slip sanitisation.  A zip entry containing path-traversal "
        "sequences (e.g. ../../evil) can write files outside the "
        "extraction directory.  Required mitigation: pass filter='data' "
        "(Python 3.12+), or canonicalise each member path "
        "(os.path.realpath / os.path.abspath) AND verify containment "
        "(os.path.commonpath / Path.is_relative_to / startswith)."
    )
