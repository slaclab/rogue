#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Audit repros for PYR-007 and PYR-008.
#   Both pickle.loads() call-sites in _Virtual.py (_remoteAttr line 682 and
#   _doUpdate line 707) deserialise network bytes without restriction.
#   These source-text tests assert the pattern is absent; on HEAD both are
#   present, so both tests FAIL.
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


def _get_method_source(cls, method_name):
    """Return source lines for a method, or empty string if unavailable."""
    try:
        return inspect.getsource(getattr(cls, method_name))
    except (OSError, TypeError):
        return ""


def test_virtual_remoteattr_pickle_loads_pyr_007():
    """PYR-007: VirtualClient._remoteAttr uses raw pickle.loads on server response."""
    from pyrogue.interfaces._Virtual import VirtualClient

    src = _get_method_source(VirtualClient, "_remoteAttr")
    assert src, "Could not retrieve source for VirtualClient._remoteAttr"

    assert "pickle.loads" not in src, (
        "PYR-007: VirtualClient._remoteAttr uses raw pickle.loads on "
        "attacker-controllable server response bytes (line 682); "
        "a compromised or spoofed server achieves code execution on the client"
    )


def test_virtual_doupdate_pickle_loads_pyr_008():
    """PYR-008: VirtualClient._doUpdate uses raw pickle.loads on ZMQ SUB bytes."""
    from pyrogue.interfaces._Virtual import VirtualClient

    src = _get_method_source(VirtualClient, "_doUpdate")
    assert src, "Could not retrieve source for VirtualClient._doUpdate"

    assert "pickle.loads" not in src, (
        "PYR-008: VirtualClient._doUpdate uses raw pickle.loads on "
        "attacker-controllable ZMQ publish bytes (line 707); "
        "a publish-channel injection achieves code execution on every subscriber"
    )
