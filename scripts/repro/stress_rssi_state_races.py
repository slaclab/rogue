#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""
DETECTED-IDs:
  - PROTO-RSSI-002
  - PROTO-RSSI-003
  - PROTO-RSSI-004

Stress the RSSI Controller lock-free state_/txListCount_ reads:
  - PROTO-RSSI-002 : state_ read in transportRx vs runThread write under stMtx_
  - PROTO-RSSI-003 : txListCount_ busy-wait lock-free read
  - PROTO-RSSI-004 : getOpen() lock-free state_ read from Python thread

macOS skip is mandatory (PROTO-RSSI-006 — default RSSI retransmission timeouts
are tighter than macOS loopback scheduling can sustain, producing spurious
timeouts).
"""
import threading

import pytest
import rogue

from conftest import skip_on_macos

pytestmark = [pytest.mark.repro, skip_on_macos]


def _build_rssi_loopback(port_base):
    """Construct a UDP-Server → RSSI-Controller → Packetizer-V2 loopback chain.

    Returns (server, client, rssi, pack) — callers must keep all refs alive.
    """
    server = rogue.protocols.udp.Server(port_base, False)
    client = rogue.protocols.udp.Client("127.0.0.1", port_base, False)
    rssi = rogue.protocols.rssi.Client(server.maxPayload())
    pack = rogue.protocols.packetizer.CoreV2(False, True, False)

    # Wire the transport side: UDP client ↔ RSSI transport
    client._setSlave(rssi.transport())
    rssi.transport()._setSlave(client)

    # Wire the application side: RSSI app ↔ Packetizer transport
    rssi.application()._setSlave(pack.transport())
    pack.transport()._setSlave(rssi.application())

    return server, client, rssi, pack


@pytest.mark.repro
def test_stress_rssi_state_read(stress_iters):
    """Concurrent getOpen() polling races transportRx state_ write (PROTO-RSSI-002/004)."""
    errors = []

    server, client, rssi, pack = _build_rssi_loopback(20090)

    def poller():
        for _ in range(stress_iters // 10):
            try:
                _ = rssi.getOpen()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=poller) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    rssi.stop()
    # Keep refs alive until return; Python GC handles teardown.
    _ = (server, client, pack)
    assert not errors, f"RSSI state_read stress errors: {errors}"


@pytest.mark.repro
def test_stress_rssi_txlistcount_busy_wait(stress_iters):
    """txListCount_ busy-wait lock-free read from Python thread (PROTO-RSSI-003)."""
    errors = []

    server, client, rssi, pack = _build_rssi_loopback(20190)

    def poller():
        for _ in range(stress_iters // 10):
            try:
                _ = rssi.getLocBusy()
                _ = rssi.getRemBusy()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=poller) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    rssi.stop()
    _ = (server, client, pack)
    assert not errors, f"RSSI txListCount stress errors: {errors}"


@pytest.mark.repro
def test_stress_rssi_concurrent_state_transitions(stress_iters):
    """Rapid Controller construction/destruction drives state_ transitions under load."""
    errors = []

    def cycle(i):
        for j in range(stress_iters // 10):
            try:
                server, client, rssi, pack = _build_rssi_loopback(20290 + i * 50 + (j % 40))
                _ = rssi.getOpen()
                rssi.stop()
                del pack
                del rssi
                del client
                del server
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=cycle, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"RSSI state-transition stress errors: {errors}"
