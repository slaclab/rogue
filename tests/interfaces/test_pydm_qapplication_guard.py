#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Regression test for the dual-QApplication "not responding" bug.

Constructing a plain QApplication before runPyDM (a pattern seen in some
downstream rogue users) leaves PyDM's window-management hooks (XSync counter,
_NET_WM_PING reply) bound to a stub instance. The visible windows then fail
to reply to compositor ping/sync messages and get flagged as "not responding"
on GNOME-on-Wayland with XWayland. runPyDM detects and rejects this pattern
with a RuntimeError naming the cause.

The body of the regression runs in a subprocess. ``QApplication.quit()`` does
not destroy the singleton, so a plain ``QApplication`` constructed in-process
would leak across files that share the same pytest-xdist worker (``--dist
loadfile``) and break sibling tests that subsequently invoke runPyDM. A
subprocess scopes the QApplication lifetime to one Python process and gives
us a clean exit code / stderr to assert against.
"""

import os
import subprocess
import sys
import textwrap

import pytest


_GUARD_SCRIPT = textwrap.dedent('''
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import sys

    # Optional Qt dependencies. Their absence means we cannot exercise
    # the dual-QApplication scenario at all, so skip with exit code 2.
    try:
        import pydm
        from qtpy.QtWidgets import QApplication
    except Exception as exc:
        sys.stderr.write(f"DEPS_MISSING:{exc}\\n")
        sys.exit(2)

    # pyrogue.pydm is the system under test. A broken import here is a
    # real failure in the code this regression locks down, NOT a missing
    # dependency, so let it propagate as a non-zero exit + traceback to
    # stderr. Lumping it with the DEPS_MISSING block above turns SUT
    # breakage into a misleading silent skip in the parent test.
    import pyrogue.pydm

    existing_app = QApplication.instance()
    if existing_app is None:
        existing_app = QApplication([])
    if isinstance(existing_app, pydm.PyDMApplication):
        sys.stderr.write("PRECONDITION_VIOLATED: existing_app is PyDMApplication\\n")
        sys.exit(3)

    detected_cls = type(existing_app)
    detected_name = f"{detected_cls.__module__}.{detected_cls.__qualname__}"
    sys.stdout.write(f"DETECTED_TYPE:{detected_name}\\n")

    try:
        pyrogue.pydm.runPyDM(serverList="localhost:9099")
    except RuntimeError as exc:
        sys.stdout.write("RUNTIMEERROR_BEGIN\\n")
        sys.stdout.write(str(exc))
        sys.stdout.write("\\nRUNTIMEERROR_END\\n")
        sys.exit(0)
    sys.stderr.write("NO_EXCEPTION_RAISED\\n")
    sys.exit(1)
''')


def _pydm_available() -> bool:
    # Mirror only the OPTIONAL Qt deps the subprocess gates on (pydm,
    # qtpy) so the parent decoration-time skip stays in sync with the
    # subprocess's DEPS_MISSING exit. We deliberately do NOT import
    # pyrogue.pydm here: it is the system under test, and an import
    # failure there must surface as a real test failure (loud), not as
    # a silent skip. The subprocess preamble mirrors that split.
    #
    # These imports do NOT load any Qt platform plugin: qtpy.QtWidgets and
    # pydm only define Python classes, and Qt's platform plugin loads
    # lazily at first QApplication(...) construction. So QT_QPA_PLATFORM
    # is intentionally not set here; it is set inside the subprocess,
    # which is the only place a QApplication is actually instantiated.
    # Empirically verified by ubuntu-24.04 CI (no DISPLAY, no
    # QT_QPA_PLATFORM) collecting and running this test rather than
    # skipping it.
    try:
        import pydm  # noqa: F401
        from qtpy.QtWidgets import QApplication  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _pydm_available(), reason="PyDM/Qt test dependencies unavailable")
def test_runPyDM_rejects_plain_qapplication():
    """Plain QApplication before runPyDM must raise RuntimeError that names
    QApplication, PyDMApplication, and the detected application class."""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"

    result = subprocess.run(
        [sys.executable, "-c", _GUARD_SCRIPT],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )

    if result.returncode == 2:
        pytest.skip(f"PyDM/Qt unavailable in subprocess: {result.stderr.strip()}")

    assert result.returncode == 0, (
        f"Subprocess exit={result.returncode}\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    stdout = result.stdout
    assert "RUNTIMEERROR_BEGIN" in stdout and "RUNTIMEERROR_END" in stdout, (
        f"runPyDM did not raise RuntimeError. stdout:\n{stdout}\nstderr:\n{result.stderr}"
    )
    msg = stdout.split("RUNTIMEERROR_BEGIN\n", 1)[1].split("\nRUNTIMEERROR_END", 1)[0]

    assert "QApplication" in msg, "Diagnostic must name QApplication as the cause"
    assert "PyDMApplication" in msg, (
        "Diagnostic must explain that PyDMApplication is required"
    )

    detected_line = next(
        (line for line in stdout.splitlines() if line.startswith("DETECTED_TYPE:")),
        None,
    )
    assert detected_line is not None, f"Subprocess did not report detected type. stdout:\n{stdout}"
    detected_name = detected_line.split(":", 1)[1].strip()
    # Non-empty + class-shape guards prevent the substring assertion below from
    # trivially passing on `"" in msg` if the marker line is ever malformed.
    assert detected_name, (
        f"DETECTED_TYPE marker carries no class name. stdout:\n{stdout}"
    )
    assert "QApplication" in detected_name, (
        f"Detected class {detected_name!r} is not a QApplication subclass; "
        f"test precondition was probably violated. stdout:\n{stdout}"
    )
    assert detected_name in msg, (
        f"Diagnostic must name the detected application class {detected_name!r}. "
        f"Message:\n{msg}"
    )

    # Verify the logging.error() call emits the diagnostic to stderr before
    # the exception propagates, so the message survives caller code that
    # wraps runPyDM in `try/finally: sys.exit(...)` and swallows exceptions.
    assert "runPyDM detected a pre-existing QApplication" in result.stderr, (
        "runPyDM did not emit the logging.error() diagnostic to stderr; the "
        "stderr-first path that survives try/finally exception swallowers "
        f"is broken.\nstderr:\n{result.stderr}"
    )
    assert detected_name in result.stderr, (
        "Logged diagnostic must also name the detected application "
        f"class {detected_name!r}.\nstderr:\n{result.stderr}"
    )
