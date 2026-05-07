#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression tests pinning post-fix invariants for RogueConnection and
#   parseAddress:
#   * remove_listener must not call self._client.stop() — the VirtualClient
#     is shared across all channels bound to the same server endpoint.
#   * RogueConnection.__init__ must None-guard self._client before calling
#     addLinkMonitor (self._client is None on non-pydm-app paths).
#   * _updateVariable must route bool values via int/object signal — PyDM
#     has no registered bool overload for new_value_signal.
#   * parseAddress must bounds-check the server index and reject negatives.
#
#   The first three tests use source-text inspection to avoid needing a
#   live server; the parseAddress test is behavioural.  A module-level
#   try/except ImportError fallback skips the file when the PyDM/Qt stack
#   is not installed, while letting other failure modes surface as real
#   regressions.
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
    # ImportError only — other exceptions are real regressions, not missing deps.
    pytest.skip("PyDM/Qt test dependencies unavailable: " + str(exc), allow_module_level=True)


# ---------------------------------------------------------------------------
# remove_listener must not stop the shared VirtualClient
# ---------------------------------------------------------------------------
def test_remove_listener_does_not_kill_shared_client():
    """remove_listener must not call self._client.stop() on the shared client.

    Post-fix invariant: removing a single channel must not tear down the
    VirtualClient shared by every other channel bound to the same server
    endpoint.  Historical regression: pre-fix HEAD called self._client.stop()
    unconditionally inside remove_listener.
    """
    src = inspect.getsource(rogue_plugin_mod.RogueConnection.remove_listener)

    assert "self._client.stop()" not in src, (
        "RogueConnection.remove_listener calls self._client.stop() "
        "unconditionally; removing any single channel tears down the shared "
        "VirtualClient for all channels bound to the same server endpoint"
    )


# ---------------------------------------------------------------------------
# RogueConnection.__init__ must guard self._client before addLinkMonitor
# ---------------------------------------------------------------------------
def test_addlinkmonitor_guards_none_client():
    """__init__ must None-guard self._client before calling addLinkMonitor.

    Post-fix invariant: the addLinkMonitor call is reachable only when
    self._client is not None.  Historical regression: pre-fix HEAD called
    self._client.addLinkMonitor(self.linkState) unconditionally, so non-pydm
    code paths (where self._client is left unset) raised AttributeError on
    construction.
    """
    src = inspect.getsource(rogue_plugin_mod.RogueConnection.__init__)
    lines = src.splitlines()

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
                "preceding None guard; self._client is only assigned a "
                "VirtualClient when utilities.is_pydm_app() is True — on "
                "other code paths self._client is None and the unguarded "
                "call raises AttributeError"
            )
            return

    raise AssertionError(
        "Could not find self._client.addLinkMonitor call in "
        "RogueConnection.__init__ — file structure may have changed"
    )


# ---------------------------------------------------------------------------
# _updateVariable signal routing must handle bool values
# ---------------------------------------------------------------------------
def test_signal_routing_handles_bool():
    """_updateVariable must route bool values via int/object, not signal[bool].

    Post-fix invariant: bool values are dispatched through a registered
    PyDM signal type (int, or an explicit isinstance(..., bool) coercion).
    Historical regression: pre-fix HEAD emitted
    new_value_signal[type(varValue.value)] for every type, and bool is not
    a registered new_value_signal key, so PyDM raised KeyError on every
    bool update.
    """
    src = inspect.getsource(rogue_plugin_mod.RogueConnection._updateVariable)

    has_bool_handling = (
        "isinstance(varValue.value, bool)" in src
        or "bool" in src.split("new_value_signal")[0]  # bool check before signal dispatch
        or "type(varValue.value) is bool" in src
    )

    has_type_dispatch = "new_value_signal[type(varValue.value)]" in src

    if has_type_dispatch:
        assert has_bool_handling, (
            "RogueConnection._updateVariable emits "
            "new_value_signal[type(varValue.value)] without handling the "
            "bool case; PyDM raises KeyError on new_value_signal[bool] "
            "because bool is not a registered signal type"
        )
    else:
        # Fallback: type dispatch refactored away but bool must still be handled.
        assert has_bool_handling, (
            "_updateVariable does not contain bool handling and "
            "the new_value_signal[type(...)] dispatch is also absent — "
            "file structure may have changed"
        )


# ---------------------------------------------------------------------------
# parseAddress must bounds-check the alist index
# ---------------------------------------------------------------------------
def test_parseaddress_bounds_check(monkeypatch):
    """parseAddress must reject out-of-range and negative server indices.

    Post-fix invariant (behavioural): with ROGUE_SERVERS set to a known
    two-entry list, addresses indexing outside ``[0, 2)`` raise
    ``IndexError``.  Two cases:
      * Out-of-range positive index (``rogue://5/...``).
      * Negative index (``rogue://-1/...``) — explicitly rejected so Python's
        negative indexing cannot silently select the last entry.

    Historical regression: pre-fix parseAddress indexed
    ``alist[int(data[0])]`` without a bounds check, so out-of-range positive
    indices raised an unhelpful traceback and negative indices silently
    selected an arbitrary server.

    Tests behaviour rather than source tokens so the fix shape (explicit
    if-guard, range membership, helper function, ...) is unconstrained.
    """
    monkeypatch.setenv("ROGUE_SERVERS", "host1:9099,host2:9099")

    with pytest.raises(IndexError):
        rogue_plugin_mod.parseAddress("rogue://5/Some/Path")

    with pytest.raises(IndexError):
        rogue_plugin_mod.parseAddress("rogue://-1/Some/Path")
