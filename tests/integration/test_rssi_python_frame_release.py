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
"""Regression: RSSI must release Python-owned retransmit frames under the GIL.

Each rssi::Header owns the FramePtr it wraps, and Controller::applicationRx()
wraps the caller's frame without copying it. A frame allocated from Python
therefore enters the retransmit list still carrying the Boost.Python
shared_ptr_deleter that owns the PyObject. That deleter calls Py_DECREF without
acquiring the GIL, so releasing it from the transport or controller thread
(neither of which holds a PyThreadState) aborted the interpreter with
"PyThreadState_Get: the function must be called with the GIL held".

Only reproduces on an OPEN connection: applicationRx() returns early while
state_ != StOpen, so frames never reach the retransmit list before the
handshake completes.

Runs in a subprocess because the unpatched failure is a fatal interpreter abort,
which would take down the xdist worker rather than failing this test.
"""

import subprocess
import sys
import textwrap

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform == "darwin",
        reason="RSSI timing too sensitive for macOS UDP stack"
    ),
]

CHILD = textwrap.dedent(
    """
    import sys
    import time

    import rogue.interfaces.stream as ris
    import rogue.protocols.rssi
    import rogue.protocols.udp

    udpSrv = rogue.protocols.udp.Server(0, True)
    udpCli = rogue.protocols.udp.Client("127.0.0.1", udpSrv.getPort(), True)

    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiCli = rogue.protocols.rssi.Client(1400)

    udpSrv == rssiSrv.transport()
    udpCli == rssiCli.transport()

    rssiSrv._start()
    rssiCli._start()

    # Frames only reach the retransmit list once the handshake completes.
    deadline = time.time() + 20.0
    while time.time() < deadline and not (rssiCli.getOpen() and rssiSrv.getOpen()):
        time.sleep(0.01)

    if not (rssiCli.getOpen() and rssiSrv.getOpen()):
        print("HANDSHAKE_TIMEOUT")
        sys.exit(2)

    src = ris.Master()
    sink = ris.Slave()
    src >> rssiCli.application()
    rssiSrv.application() >> sink

    for _ in range(40):
        frame = src._reqFrame(512, True)
        frame.write(bytearray(512), 0)
        src._sendFrame(frame)

        # Drop the Python-side reference so the retransmit list owns the last
        # one; acks then release it from the transport thread.
        del frame
        time.sleep(0.01)

    time.sleep(1.0)

    rssiCli._stop()
    rssiSrv._stop()

    print("OK")
    """
)


def test_rssi_releases_python_owned_retransmit_frames():
    result = subprocess.run(
        [sys.executable, "-c", CHILD],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if "HANDSHAKE_TIMEOUT" in result.stdout:
        pytest.skip("RSSI handshake did not open in time on this host")

    # An unpatched build dies on SIGABRT from the fatal Python error, so a clean
    # exit is the assertion. Report the child's own diagnostics on failure.
    assert result.returncode == 0, (
        f"child exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK" in result.stdout
