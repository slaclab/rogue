#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
# Description:
#   Regression test.
#   system_log.py value_changed() calls json.loads(new_val) bare;
#             a non-JSON string raises json.JSONDecodeError in a Qt slot.
#
#    and  were dropped during Phase-3 triage
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
    # Skip only when the PyDM / Qt stack is not installed.  Other failure
    # modes (SyntaxError, NameError, AttributeError, ...) are real product
    # regressions and must surface as test failures rather than silently
    # turning into a skip.
    pytest.skip("PyDM/Qt test dependencies unavailable: " + str(exc), allow_module_level=True)


# ---------------------------------------------------------------------------
# system_log value_changed bare json.loads
# ---------------------------------------------------------------------------
def test_system_log_value_changed_handles_json_error():
    """system_log.value_changed calls json.loads without try/except."""
    src = inspect.getsource(system_log_mod.SystemLog.value_changed)

    assert "try:" in src, (
        "SystemLog.value_changed() calls json.loads(new_val) "
        "(line 84) without a try/except; a non-JSON string emitted by the "
        "SystemLog variable during startup raises json.JSONDecodeError in a "
        "Qt slot, which is silently swallowed but may corrupt widget state"
    )
