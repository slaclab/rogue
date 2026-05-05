#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
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


def test_virtual_remoteattr_pickle_loads():
    """VirtualClient._remoteAttr uses raw pickle.loads on server response."""
    from pyrogue.interfaces._Virtual import VirtualClient

    src = _get_method_source(VirtualClient, "_remoteAttr")
    assert src, "Could not retrieve source for VirtualClient._remoteAttr"

    assert "pickle.loads" not in src, (
        "VirtualClient._remoteAttr uses raw pickle.loads on "
        "attacker-controllable server response bytes (line 682); "
        "a compromised or spoofed server achieves code execution on the client"
    )


def test_virtual_doupdate_pickle_loads():
    """VirtualClient._doUpdate uses raw pickle.loads on ZMQ SUB bytes."""
    from pyrogue.interfaces._Virtual import VirtualClient

    src = _get_method_source(VirtualClient, "_doUpdate")
    assert src, "Could not retrieve source for VirtualClient._doUpdate"

    assert "pickle.loads" not in src, (
        "VirtualClient._doUpdate uses raw pickle.loads on "
        "attacker-controllable ZMQ publish bytes (line 707); "
        "a publish-channel injection achieves code execution on every subscriber"
    )


def test_virtual_safe_loads_decodes_server_error_reply():
    """Client unpickler must accept the Exception object that
    ZmqServer._doRequest sends on every error reply.

    ZmqServer._doRequest wraps every server-side failure as
    ``Exception(type_qualified_msg)`` and pickles that for transport.
    If the client-side _VirtualSafeUnpickler does not allowlist
    ``builtins.Exception`` then every legitimate remote error becomes an
    UnpicklingError on the client and the original failure is lost.
    """
    import pickle

    from pyrogue.interfaces._Virtual import _virtual_safe_loads

    payload = pickle.dumps(Exception("simulated server-side error"))
    result = _virtual_safe_loads(payload)

    assert isinstance(result, Exception), (
        f"client _virtual_safe_loads must accept builtins.Exception "
        f"replies; got {type(result).__name__}"
    )
    assert "simulated server-side error" in str(result)


def test_virtual_safe_loads_still_rejects_arbitrary_builtins():
    """Client unpickler must keep rejecting non-data builtins so the
    pickle REDUCE arbitrary-code-execution path stays closed even after
    Exception is allowed for the error-reply contract.
    """
    import pickle

    from pyrogue.interfaces._Virtual import _virtual_safe_loads

    # Hand-roll a pickle stream that references builtins.eval via GLOBAL
    # so we exercise find_class without depending on whether eval is
    # actually picklable in the running interpreter.
    payload = b"cbuiltins\neval\n."
    try:
        _virtual_safe_loads(payload)
    except pickle.UnpicklingError:
        return
    raise AssertionError(
        "client unpickler accepted builtins.eval; the broader "
        "_ALLOWED_BUILTINS allowlist must stay restricted to data types "
        "(plus Exception for server-error replies)"
    )
