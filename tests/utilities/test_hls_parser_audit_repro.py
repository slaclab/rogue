#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test for a prior zip-slip vulnerability in
#   _RegInterfParser.parse().  The previous implementation called
#   ZipFile.extractall() without sanitising zip entry names against path
#   traversal, allowing crafted entries to escape the extraction directory.
#   This test enforces the invariant that parse() carries a zip-slip
#   mitigation: canonicalise each member path AND verify containment
#   against the extraction directory.  Failure of this assertion indicates
#   the mitigation has been removed/regressed.
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
    """_RegInterfParser.parse() retains zip-slip mitigation around extractall()."""
    src = inspect.getsource(parser_mod.parse)

    has_canonicalisation = (
        "os.path.realpath" in src or "os.path.abspath" in src
    )
    has_containment = (
        "os.path.commonpath" in src
        or "is_relative_to" in src
        or ".startswith(" in src
    )
    has_mitigation = has_canonicalisation and has_containment

    assert has_mitigation, (
        "_RegInterfParser.parse() calls ZipFile.extractall() without "
        "zip-slip sanitisation.  A zip entry containing path-traversal "
        "sequences (e.g. ../../evil) can write files outside the "
        "extraction directory.  Required mitigation: canonicalise each "
        "member path (os.path.realpath / os.path.abspath) AND verify "
        "containment (os.path.commonpath / Path.is_relative_to / "
        "startswith)."
    )
