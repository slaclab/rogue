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

import sys
import time

import rogue
import rogue.protocols.udp
import rogue.protocols.rssi
import rogue.utilities
import pytest

from conftest import wait_for

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform == "darwin",
        reason="RSSI timing too sensitive for macOS UDP stack"
    ),
]

CONNECTION_TIMEOUT = 15.0
STALL_WINDOW = 5.0
POLL_INTERVAL = 0.01


def wait_for_progress(get_value, target, label):
    """Block until get_value() reaches target with progress-based stall detection."""
    last_value = get_value()
    last_change = time.monotonic()
    while True:
        current = get_value()
        if current >= target:
            return current
        if current != last_value:
            last_value = current
            last_change = time.monotonic()
        elif (time.monotonic() - last_change) > STALL_WINDOW:
            raise AssertionError(
                f"{label} stalled at {current}/{target} "
                f"after {STALL_WINDOW:.1f}s with no progress"
            )
        time.sleep(POLL_INTERVAL)


def test_rssi_handshake_opens():
    udpSrv = rogue.protocols.udp.Server(0, True)
    port = udpSrv.getPort()
    udpCli = rogue.protocols.udp.Client("127.0.0.1", port, True)

    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiCli = rogue.protocols.rssi.Client(1400)

    udpSrv == rssiSrv.transport()
    udpCli == rssiCli.transport()

    rssiSrv._start()
    rssiCli._start()

    try:
        assert wait_for(
            lambda: rssiCli.getOpen() and rssiSrv.getOpen(),
            timeout=CONNECTION_TIMEOUT
        ), "RSSI link did not open"
    finally:
        rssiCli._stop()
        rssiSrv._stop()


def test_rssi_data_transfer():
    udpSrv = rogue.protocols.udp.Server(0, True)
    port = udpSrv.getPort()
    udpCli = rogue.protocols.udp.Client("127.0.0.1", port, True)

    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiCli = rogue.protocols.rssi.Client(1400)

    udpSrv == rssiSrv.transport()
    udpCli == rssiCli.transport()

    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()
    prbsRx.checkPayload(True)

    rssiCli.application() << prbsTx
    prbsRx << rssiSrv.application()

    rssiSrv._start()
    rssiCli._start()

    try:
        assert wait_for(
            lambda: rssiCli.getOpen() and rssiSrv.getOpen(),
            timeout=CONNECTION_TIMEOUT
        ), "RSSI link did not open"

        frame_count = 100
        frame_size = 256
        for _ in range(frame_count):
            prbsTx.genFrame(frame_size)

        wait_for_progress(prbsRx.getRxCount, frame_count, "RSSI RX")
        assert prbsRx.getRxErrors() == 0
    finally:
        rssiCli._stop()
        rssiSrv._stop()


def test_rssi_retransmit_counter_zero_clean_path():
    udpSrv = rogue.protocols.udp.Server(0, True)
    port = udpSrv.getPort()
    udpCli = rogue.protocols.udp.Client("127.0.0.1", port, True)

    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiCli = rogue.protocols.rssi.Client(1400)

    # The default RSSI retransmit timeout is 20 ms (Controller.cpp's
    # locRetranTout_ init with TimeoutUnit=3 => ms).  Under pytest-xdist
    # (3 workers on macOS arm64 runners) the 20 ms window is tight enough
    # that ACK delivery jitter routinely exceeds it and RSSI retransmits
    # even though every frame arrived intact — observed as 14/50 spurious
    # retransmits in CI.  Bump to 200 ms so the timer tolerates scheduler
    # jitter on busy runners.  Both sides negotiate this in the SYN
    # handshake, so setting it on both ends pins the on-the-wire value.
    rssiSrv.setLocRetranTout(200)
    rssiCli.setLocRetranTout(200)

    udpSrv == rssiSrv.transport()
    udpCli == rssiCli.transport()

    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()
    prbsRx.checkPayload(True)

    rssiCli.application() << prbsTx
    prbsRx << rssiSrv.application()

    rssiSrv._start()
    rssiCli._start()

    try:
        assert wait_for(
            lambda: rssiCli.getOpen() and rssiSrv.getOpen(),
            timeout=CONNECTION_TIMEOUT
        )

        for _ in range(50):
            prbsTx.genFrame(128)

        wait_for_progress(prbsRx.getRxCount, 50, "RSSI RX clean")
        assert prbsRx.getRxErrors() == 0

        assert rssiCli.getRetranCount() == 0
        assert rssiSrv.getRetranCount() == 0
    finally:
        rssiCli._stop()
        rssiSrv._stop()


def test_rssi_graceful_shutdown():
    udpSrv = rogue.protocols.udp.Server(0, True)
    port = udpSrv.getPort()
    udpCli = rogue.protocols.udp.Client("127.0.0.1", port, True)

    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiCli = rogue.protocols.rssi.Client(1400)

    udpSrv == rssiSrv.transport()
    udpCli == rssiCli.transport()

    rssiSrv._start()
    rssiCli._start()

    try:
        assert wait_for(
            lambda: rssiCli.getOpen(),
            timeout=CONNECTION_TIMEOUT
        )
    finally:
        rssiCli._stop()
        rssiSrv._stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
