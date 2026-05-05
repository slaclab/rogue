#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   remove_listener calls self._client.stop() unconditionally,
#             tearing down the shared VirtualClient for all channels.
#   add_listener calls self._client.addLinkMonitor(...)
#             unconditionally; self._client may be None on non-pydm-app paths.
#   _updateVariable emits new_value_signal[type(varValue.value)]
#             without handling bool; PyDM raises KeyError on bool type.
#   parseAddress indexes alist[int(data[0])] without bounds check;
#             out-of-range index raises IndexError.
#
#   All four tests use source-text inspection to avoid needing a live server.
#   Module-level importorskip ensures graceful skip when PyDM is unavailable.
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

import pytest

try:
    import pyrogue.pydm.data_plugins.rogue_plugin as rogue_plugin_mod
except ImportError as exc:
    # Skip only when the PyDM / Qt stack is not installed.  Other failure
    # modes (SyntaxError, NameError, AttributeError, ...) are real product
    # regressions and must surface as test failures rather than silently
    # turning into a skip.
    pytest.skip("PyDM/Qt test dependencies unavailable: " + str(exc), allow_module_level=True)


# ---------------------------------------------------------------------------
# remove_listener calls self._client.stop() unconditionally
# ---------------------------------------------------------------------------
def test_remove_listener_does_not_kill_shared_client():
    """remove_listener calls self._client.stop() unconditionally."""
    src = inspect.getsource(rogue_plugin_mod.RogueConnection.remove_listener)

    # A correct implementation would only call stop() when the last listener
    # is removed, or not at all (since the VirtualClient is shared).
    # On HEAD an unconditional self._client.stop() is present.
    assert "self._client.stop()" not in src, (
        "RogueConnection.remove_listener calls self._client.stop() "
        "unconditionally; removing any single channel tears down the shared "
        "VirtualClient for all channels bound to the same server endpoint"
    )


# ---------------------------------------------------------------------------
# add_listener calls addLinkMonitor without guarding None client
# ---------------------------------------------------------------------------
def test_addlinkmonitor_guards_none_client():
    """RogueConnection.__init__ calls addLinkMonitor without None guard."""
    src = inspect.getsource(rogue_plugin_mod.RogueConnection.__init__)
    lines = src.splitlines()

    # Find the addLinkMonitor call and check that a None-guard appears
    # within the preceding 5 lines.
    for i, line in enumerate(lines):
        if "self._client.addLinkMonitor" in line:
            context = lines[max(0, i - 5):i]
            context_text = "\n".join(context)
            has_guard = (
                "if self._client is None" in context_text
                or "if self._client is not None" in context_text
                or "_client is not None" in context_text
            )
            assert has_guard, (
                "RogueConnection.__init__ calls "
                "self._client.addLinkMonitor(self.linkState) without a "
                "preceding None guard (line 148); self._client is only set "
                "when utilities.is_pydm_app() is True — on other code paths "
                "self._client is undefined and raises AttributeError"
            )
            return

    raise AssertionError(
        "Could not find self._client.addLinkMonitor call in "
        "RogueConnection.__init__ — file structure may have changed"
    )


# ---------------------------------------------------------------------------
# _updateVariable signal routing does not handle bool type
# ---------------------------------------------------------------------------
def test_signal_routing_handles_bool():
    """_updateVariable emits signal[type(value)] without handling bool."""
    src = inspect.getsource(rogue_plugin_mod.RogueConnection._updateVariable)

    # PyDM's new_value_signal does not have a [bool] key.
    # The fix either coerces bool to int before dispatch or adds an
    # explicit isinstance(varValue.value, bool) check.
    has_bool_handling = (
        "isinstance(varValue.value, bool)" in src
        or "bool" in src.split("new_value_signal")[0]  # bool check before signal dispatch
        or "type(varValue.value) is bool" in src
    )

    # Also check that the raw type dispatch is present (confirming the bug exists)
    has_type_dispatch = "new_value_signal[type(varValue.value)]" in src

    if has_type_dispatch:
        assert has_bool_handling, (
            "RogueConnection._updateVariable emits "
            "new_value_signal[type(varValue.value)] (line 205) without "
            "handling the bool case; PyDM raises KeyError on "
            "new_value_signal[bool] because bool is not a registered signal type"
        )
    else:
        # If raw type dispatch is gone, the signal may have been refactored;
        # assert bool is still handled
        assert has_bool_handling, (
            "_updateVariable does not contain bool handling and "
            "the new_value_signal[type(...)] dispatch is also absent — "
            "file structure may have changed"
        )


# ---------------------------------------------------------------------------
# parseAddress lacks bounds check on alist index
# ---------------------------------------------------------------------------
def test_parseaddress_bounds_check():
    """parseAddress indexes alist[int(data[0])] without bounds check."""
    src = inspect.getsource(rogue_plugin_mod.parseAddress)

    # A correct fix needs to reject indexes outside [0, len(alist)) — the
    # original bug was both an out-of-range crash and Python's negative-
    # indexing silently selecting an arbitrary server (e.g. ``rogue://-1/...``
    # picking the last entry).  Require evidence of both:
    #   (a) An upper-bound check against len(alist) OR an explicit
    #       IndexError raise to surface the failure with a clear message.
    #   (b) A negative-index reject (``idx < 0`` or ``< 0``-equivalent).
    # A bare ``"try:"`` clause is intentionally NOT accepted: a
    # ``try/except IndexError`` silently consumes the failure, which is a
    # worse bug than the original confusing traceback.
    has_upper_bound = ("len(alist)" in src) or ("raise IndexError" in src)
    has_negative_reject = ("idx < 0" in src) or ("< 0" in src)

    assert has_upper_bound and has_negative_reject, (
        "parseAddress() indexes alist[int(data[0])] without a complete "
        "bounds check; needs both an upper bound (len(alist) or raise "
        "IndexError) AND a negative-index reject (idx < 0).  Without the "
        "negative reject, addresses like ``rogue://-1/...`` silently "
        "select the last ROGUE_SERVERS entry via Python's negative "
        "indexing rather than reporting invalid input."
    )
