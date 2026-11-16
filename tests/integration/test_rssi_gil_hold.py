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
"""Regression: an open RSSI link must survive another thread holding the GIL.

Controller::releaseHeaders() runs on the transport thread for every received
ACK and on every transmit. When it took the GIL unconditionally, any thread
holding the GIL (a PyDM/Qt GUI building its window over X11 forwarding, for
example) stalled the client's ACKs and NULLs past the NULL timeout, the peer
reset the link, and every in-flight SRP transaction timed out. Only frames
handed in from Python need the GIL to release, and this link carries none.

The server runs in a child process so, like an FPGA peer, it keeps running
while this process holds its GIL. The GIL is held with a PyDLL call, which
never releases it, so the stall is a fixed wall-clock duration rather than a
CPU-speed-dependent loop.
"""

import ctypes
import subprocess
import sys
import textwrap
import time

import pytest

import rogue.protocols.rssi
import rogue.protocols.udp

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform == "darwin",
        reason="RSSI timing too sensitive for macOS UDP stack"
    ),
]

NULL_TOUT_MS = 300
GIL_HOLD_S = 10 * NULL_TOUT_MS / 1000.0

SERVER = textwrap.dedent(
    f"""
    import sys

    import rogue.protocols.rssi
    import rogue.protocols.udp

    udpSrv = rogue.protocols.udp.Server(0, True)
    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiSrv.setLocNullTout({NULL_TOUT_MS})
    udpSrv == rssiSrv.transport()
    rssiSrv._start()

    print(f"PORT {{udpSrv.getPort()}}", flush=True)
    sys.stdin.readline()
    print(f"DOWN {{rssiSrv.getDownCount()}}", flush=True)
    rssiSrv._stop()
    """
)


def _wait_until(predicate, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_rssi_link_survives_gil_hold():
    server = subprocess.Popen(
        [sys.executable, "-c", SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    rssiCli = None
    try:
        line = server.stdout.readline()
        assert line.startswith("PORT "), f"server did not start: {line!r}"
        port = int(line.split()[1])

        udpCli = rogue.protocols.udp.Client("127.0.0.1", port, True)
        rssiCli = rogue.protocols.rssi.Client(1400)
        # A short NULL timeout keeps the GIL hold, and so the test, brief.
        rssiCli.setLocNullTout(NULL_TOUT_MS)
        udpCli == rssiCli.transport()
        rssiCli._start()

        if not _wait_until(rssiCli.getOpen, 20.0):
            pytest.skip("RSSI handshake did not open in time on this host")
        assert rssiCli.curNullTout() == NULL_TOUT_MS

        # Let the link carry several NULL/ACK exchanges before the stall.
        time.sleep(3 * NULL_TOUT_MS / 1000.0)
        assert rssiCli.getDownCount() == 0

        ctypes.PyDLL(None).usleep(int(GIL_HOLD_S * 1e6))

        # Give a reset from the server time to reach the client.
        time.sleep(3 * NULL_TOUT_MS / 1000.0)
        cli_down = rssiCli.getDownCount()
        cli_open = rssiCli.getOpen()

        server.stdin.write("\n")
        server.stdin.flush()
        srv_down = int(server.stdout.readline().split()[1])

        assert srv_down == 0, "Server reset the link while the client process held the GIL"
        assert cli_down == 0, "Client RSSI link reset while the GIL was held"
        assert cli_open
    finally:
        if rssiCli is not None:
            rssiCli._stop()
        if server.poll() is None:
            server.kill()
        server.wait(timeout=10)
