#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test pinning the post-fix invariant: json.loads in
#   SystemLog.value_changed must be wrapped in try/except JSONDecodeError
#   so malformed log payloads cannot abort the Qt slot.  Historical
#   regression: pre-fix HEAD called json.loads(new_val) bare.
#
#   Note: two additional widget hypotheses were dropped during Phase-3 triage
#   (DROP-hypothesis-was-wrong): their pre-fix CI repros never demonstrated
#   a real bug, so the corresponding test cases are not present in this file.
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
    from qtpy.QtWidgets import QWidget  # noqa: F401
    import pyrogue.pydm.widgets.system_log as system_log_mod
except ImportError as exc:
    # ImportError only — other exceptions are real regressions, not missing deps.
    pytest.skip("PyDM/Qt test dependencies unavailable: " + str(exc), allow_module_level=True)


# ---------------------------------------------------------------------------
# system_log value_changed bare json.loads
# ---------------------------------------------------------------------------
def test_system_log_value_changed_handles_json_error():
    """SystemLog.value_changed wraps json.loads in try/except JSONDecodeError.

    Post-fix invariant: the json.loads call in value_changed must be inside
    a try block whose except clause catches json.JSONDecodeError (or a parent
    class), so malformed log payloads cannot abort the Qt slot.  Historical
    regression: pre-fix HEAD called json.loads(new_val) bare, so a non-JSON
    string raised json.JSONDecodeError inside the slot.
    """
    import re

    src = inspect.getsource(system_log_mod.SystemLog.value_changed)

    # Pattern ties try/except to json.loads specifically — bare "try:" in src would false-pass.
    pattern = (
        r"try:.*?json\.loads.*?except\s+"
        r"(json\.JSONDecodeError|JSONDecodeError|ValueError|Exception)"
    )
    has_protected_loads = bool(re.search(pattern, src, re.DOTALL))

    assert has_protected_loads, (
        "SystemLog.value_changed() calls json.loads(new_val) without a "
        "try/except that catches json.JSONDecodeError; a non-JSON string "
        "emitted by the SystemLog variable during startup raises "
        "json.JSONDecodeError in a Qt slot, which is silently swallowed "
        "but may corrupt widget state"
    )
