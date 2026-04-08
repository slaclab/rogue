#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Data over udp/packetizer/rssi test script
#-----------------------------------------------------------------------------
# This file is part of the rogue_example software. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue_example software, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.utilities
import rogue.protocols.udp
import rogue.interfaces.stream
import rogue
import time
import threading
import pytest

pytestmark = pytest.mark.integration

# This is a protocol-stack regression test for UDP/RSSI/packetizer behavior,
# including out-of-order delivery. Smaller frame counts are enough to validate
# the path without turning the test into a stress benchmark.
FRAME_COUNT = 200
FRAME_SIZE = 2048

# Rather than an arbitrary wall-clock timeout (which fails on slow machines),
# the drain and reorder-settle loops use progress-based waiting: as long as
# the monitored counter keeps advancing we keep waiting, no matter how slow.
# We only bail out if the counter stops advancing for STALL_WINDOW seconds,
# which is a reliable indicator that the pipeline is genuinely stuck rather
# than merely slow.
STALL_WINDOW = 5.0
POLL_INTERVAL = 0.01

# RSSI open is a one-shot handshake with no incremental progress, so it still
# uses a plain bound. This has never been the flake source, but 30s gives
# plenty of headroom on loaded runners.
CONNECTION_TIMEOUT = 30.0


def wait_for_progress(get_value, target, label):
    """Block until get_value() reaches target.

    Progress-based: resets the stall clock every time the value advances,
    so arbitrarily slow machines still pass. Only raises if the counter
    stops advancing for STALL_WINDOW seconds.
    """
    last_value = get_value()
    last_change = time.time()
    while True:
        current = get_value()
        if current >= target:
            return current
        if current != last_value:
            last_value = current
            last_change = time.time()
        elif (time.time() - last_change) > STALL_WINDOW:
            raise AssertionError(
                f"{label} stalled at {current}/{target} "
                f"after {STALL_WINDOW:.1f}s with no progress"
            )
        time.sleep(POLL_INTERVAL)


class RssiOutOfOrder(rogue.interfaces.stream.Slave, rogue.interfaces.stream.Master):

    def __init__(self, period=0):
        rogue.interfaces.stream.Slave.__init__(self)
        rogue.interfaces.stream.Master.__init__(self)

        self._period = period
        self._lock   = threading.Lock()
        self._last   = None
        self._cnt    = 0

    @property
    def period(self):
        return self._period

    @period.setter
    def period(self, value):
        with self._lock:
            self._period = value

            # Send any cached frames if period is now 0
            if self._period == 0 and self._last is not None:
                self._sendFrame(self._last)
                self._last = None

    @property
    def cnt(self):
        with self._lock:
            return self._cnt

    def _acceptFrame(self, frame: rogue.interfaces.stream.Frame) -> None:

        with self._lock:
            self._cnt += 1

            # Frame is cached, send current frame before cached frame
            if self._last is not None:
                self._sendFrame(frame)
                self._sendFrame(self._last)
                self._last = None

            # Out of order period has elapsed, store frame
            elif self._period > 0 and (self._cnt % self._period) == 0:
                self._last = frame

            # Otherwise just forward the frame
            else:
                self._sendFrame(frame)


def build_packetizer_pair(version):
    """Return matching packetizer endpoints for the requested wire version."""
    if version == 1:
        return rogue.protocols.packetizer.Core(True), rogue.protocols.packetizer.Core(True)
    return rogue.protocols.packetizer.CoreV2(True, True, True), rogue.protocols.packetizer.CoreV2(True, True, True)


def run_udp_packetizer_path(version, jumbo):
    """Validate UDP/RSSI/packetizer delivery under periodic out-of-order frames."""
    server = rogue.protocols.udp.Server(0, jumbo)
    port = server.getPort()
    client = rogue.protocols.udp.Client("127.0.0.1", port, jumbo)

    server_rssi = rogue.protocols.rssi.Server(server.maxPayload() - 8)
    client_rssi = rogue.protocols.rssi.Client(client.maxPayload() - 8)

    server_pack, client_pack = build_packetizer_pair(version)

    prbs_tx = rogue.utilities.Prbs()
    prbs_rx = rogue.utilities.Prbs()
    out_of_order = RssiOutOfOrder(period=0)

    prbs_tx >> client_pack.application(0)
    client_rssi.application() == client_pack.transport()
    client_rssi.transport() >> out_of_order >> client >> client_rssi.transport()

    server == server_rssi.transport()
    server_rssi.application() == server_pack.transport()
    server_pack.application(0) >> prbs_rx

    rssi_started = False
    try:
        # Start with orderly transport first so the RSSI session comes up cleanly
        # before periodic reordering is introduced.
        server_rssi._start()
        client_rssi._start()
        rssi_started = True

        # RSSI handshake is binary (open / not open) with no incremental
        # progress, so a plain bound is appropriate here.
        open_deadline = time.time() + CONNECTION_TIMEOUT
        while not client_rssi.getOpen():
            if time.time() > open_deadline:
                raise AssertionError(f"RSSI timeout error. Ver={version} Jumbo={jumbo}")
            time.sleep(0.1)

        out_of_order.period = 10
        for _ in range(FRAME_COUNT):
            prbs_tx.genFrame(FRAME_SIZE)

        # Wait until the reordering stage has actually observed every frame
        # before flushing its cache. Otherwise a frame that lands in the cache
        # after the flush ran gets stuck there and starves the drain loop.
        wait_for_progress(
            lambda: out_of_order.cnt,
            FRAME_COUNT,
            label=f"reorder settle Ver={version} Jumbo={jumbo}",
        )

        out_of_order.period = 0

        wait_for_progress(
            lambda: prbs_rx.getRxCount(),
            FRAME_COUNT,
            label=f"frame drain Ver={version} Jumbo={jumbo}",
        )

        assert prbs_rx.getRxErrors() == 0

    finally:
        # Deterministic teardown: quiesce the reordering stage, stop RSSI
        # sessions, give in-flight C++ callbacks a moment to unwind, then
        # drop references in reverse link order so upstream stages never
        # outlive the downstream slaves they still hold pointers to.
        try:
            out_of_order.period = 0
        except Exception:
            pass
        if rssi_started:
            try:
                client_rssi._stop()
            except Exception:
                pass
            try:
                server_rssi._stop()
            except Exception:
                pass
        time.sleep(0.1)

        prbs_tx = None
        prbs_rx = None
        client_pack = None
        server_pack = None
        client_rssi = None
        server_rssi = None
        out_of_order = None
        client = None
        server = None


@pytest.mark.parametrize("version,jumbo", [(1, True), (2, True), (1, False), (2, False)])
def test_data_path(version, jumbo):
    run_udp_packetizer_path(version, jumbo)

if __name__ == "__main__":
    for version, jumbo in [(1, True), (2, True), (1, False), (2, False)]:
        run_udp_packetizer_path(version, jumbo)
