#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Functional regression tests for the rogue_plugin parseAddress bounds-check
#   path. A module-level try/except ImportError fallback skips the file when
#   the PyDM/Qt stack is not installed, while letting other failure modes
#   surface as real regressions.
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pytest

try:
    import pyrogue.pydm.data_plugins.rogue_plugin as rogue_plugin_mod
except ImportError as exc:
    # ImportError only — other exceptions are real regressions, not missing deps.
    pytest.skip("PyDM/Qt test dependencies unavailable: " + str(exc), allow_module_level=True)


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
    """
    monkeypatch.setenv("ROGUE_SERVERS", "host1:9099,host2:9099")

    with pytest.raises(IndexError):
        rogue_plugin_mod.parseAddress("rogue://5/Some/Path")

    with pytest.raises(IndexError):
        rogue_plugin_mod.parseAddress("rogue://-1/Some/Path")
