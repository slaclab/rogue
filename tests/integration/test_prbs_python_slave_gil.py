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
"""Regression: Prbs::setTaps()/resetCount() must release the GIL before pMtx_.

Prbs::genFrame() releases the GIL, locks pMtx_, and holds it across
sendFrame(). When the downstream slave is a Python object, sendFrame()
reacquires the GIL to call the Python _acceptFrame(). setTaps() and
resetCount() previously locked pMtx_ while still holding the GIL, so a Python
caller invoking either while the background TX thread was inside genFrame()
deadlocked: the Python thread held the GIL waiting on pMtx_, the TX thread
held pMtx_ waiting on the GIL.

Runs in a subprocess because the unpatched failure is a hard hang that would
otherwise stall the xdist worker rather than failing this test.
"""

import subprocess
import sys
import textwrap

import pytest

pytestmark = pytest.mark.integration

CHILD = textwrap.dedent(
    """
    import time

    import rogue.interfaces.stream as ris
    import rogue.utilities

    class PySink(ris.Slave):
        def __init__(self):
            super().__init__()
            self.count = 0

        def _acceptFrame(self, frame):
            self.count += 1

    tx = rogue.utilities.Prbs()
    sink = PySink()
    tx >> sink

    tx.enable(1024)

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        tx.resetCount()
        tx.setTaps(bytearray([1, 2, 6, 31]))

    tx.disable()

    print("OK" if sink.count > 0 else "NO_FRAMES")
    """
)


def test_prbs_set_taps_reset_count_no_deadlock_with_python_slave():
    try:
        result = subprocess.run(
            [sys.executable, "-c", CHILD],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("child hung: setTaps()/resetCount() deadlocked against genFrame()")

    assert result.returncode == 0, (
        f"child exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK" in result.stdout, result.stdout
