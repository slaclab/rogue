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
import sys
import threading
import time
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform == "darwin",
        reason="RSSI timing too sensitive for macOS UDP stack"
    ),
]

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
#
# 15s is generous on purpose: loaded CI runners under pytest-xdist can
# have multi-second windows of zero observed progress — import warm-up
# plus contention on the C++ packetizer/RSSI worker threads.
# Tightening this window only buys spurious failures, not faster
# passing runs (the loop exits immediately once the counter advances),
# so prefer a wide stall window.
STALL_WINDOW = 15.0
POLL_INTERVAL = 0.01

# RSSI open is a one-shot handshake with no incremental progress, so it still
# uses a plain bound. On loopback this should complete quickly; keep enough
# headroom for loaded CI workers without letting a bad run sit for 30 seconds.
CONNECTION_TIMEOUT = 10.0
CONNECTION_POLL_INTERVAL = 0.05
TEARDOWN_SETTLE_DELAY = 0.05


def wait_for_progress(get_value, target, label, health_check=None):
    """Block until get_value() reaches target.

    Progress-based: resets the stall clock every time the value advances,
    so arbitrarily slow machines still pass. Only raises if the counter
    stops advancing for STALL_WINDOW seconds.

    If *health_check* is provided it is called each iteration; returning
    False causes an immediate failure (used to detect RSSI session drops
    instead of waiting the full stall window for a session that is already
    dead).
    """
    last_value = get_value()
    last_change = time.monotonic()
    while True:
        current = get_value()
        if current >= target:
            return current
        if health_check is not None and not health_check():
            raise AssertionError(
                f"{label} aborted at {current}/{target}: "
                f"RSSI session closed unexpectedly"
            )
        if current != last_value:
            last_value = current
            last_change = time.monotonic()
        elif (time.monotonic() - last_change) > STALL_WINDOW:
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

    # Relax RSSI protocol parameters so the session survives CI scheduling
    # jitter on top of the intentional out-of-order injection.  Defaults
    # (retranTout=20ms, maxRetran=15, cumAckTout=5ms) are tuned for
    # real FPGA links with deterministic latency; under pytest-xdist the
    # OS thread scheduler can stall ACK delivery for tens of milliseconds,
    # exhausting the retransmit budget and closing the session (manifests
    # as 0/N frames delivered).
    for ep in (server_rssi, client_rssi):
        ep.setLocRetranTout(3000)
        ep.setLocMaxRetran(100)
        ep.setLocCumAckTout(50)
        ep.setLocNullTout(3000)

    server_pack, client_pack = build_packetizer_pair(version)

    prbs_tx = rogue.utilities.Prbs()
    prbs_rx = rogue.utilities.Prbs()
    out_of_order = RssiOutOfOrder(period=0)

    # out_of_order sits on the RSSI transport path, so its counter advances
    # once per RSSI segment — not once per PRBS application frame, and it also
    # ticks for non-data control traffic (SYN/ACK/NULL keepalives). A 2048-byte
    # frame fits in a single jumbo segment but is split into multiple segments
    # on a standard-MTU link, so we compute the exact expected data-segment
    # count from the UDP max payload and the per-packet packetizer overhead.
    # The wait below baselines `cnt` immediately before generating frames so
    # handshake/keepalive segments don't let it return early. Without these
    # two pieces, `out_of_order.cnt >= FRAME_COUNT` can become true long before
    # all generated frames have actually been observed, reintroducing the
    # reorder-drain race the wait is meant to close.
    rssi_hdr_size = 8
    pack_hdr_size = 8
    pack_tail_size = 8 if version == 2 else 1
    segment_payload = client.maxPayload() - rssi_hdr_size - pack_hdr_size - pack_tail_size
    segments_per_frame = max(1, (FRAME_SIZE + segment_payload - 1) // segment_payload)
    expected_segments = FRAME_COUNT * segments_per_frame

    prbs_tx >> client_pack.application(0)
    client_rssi.application() == client_pack.transport()
    client_rssi.transport() >> out_of_order >> client >> client_rssi.transport()

    server == server_rssi.transport()
    server_rssi.application() == server_pack.transport()
    server_pack.application(0) >> prbs_rx

    server_started = False
    client_started = False
    try:
        # Start with orderly transport first so the RSSI session comes up cleanly
        # before periodic reordering is introduced. Track each endpoint
        # separately so a failure mid-start still gets cleaned up in finally.
        server_rssi._start()
        server_started = True
        client_rssi._start()
        client_started = True

        # RSSI handshake is binary (open / not open) with no incremental
        # progress, so a plain bound is appropriate here.
        open_deadline = time.monotonic() + CONNECTION_TIMEOUT
        while not client_rssi.getOpen():
            if time.monotonic() > open_deadline:
                raise AssertionError(f"RSSI timeout error. Ver={version} Jumbo={jumbo}")
            time.sleep(CONNECTION_POLL_INTERVAL)

        out_of_order.period = 10

        # Baseline the segment counter AFTER the RSSI handshake (which itself
        # bumps cnt via SYN/ACK control frames) and immediately before we
        # start generating data frames. The wait below uses an absolute
        # target, so without this baseline the handshake/keepalive traffic
        # would let the wait return early and reintroduce the flush race.
        baseline_segments = out_of_order.cnt

        for _ in range(FRAME_COUNT):
            prbs_tx.genFrame(FRAME_SIZE)

        # Wait until the reordering stage has actually observed every segment
        # for every generated frame before flushing its cache. Otherwise a
        # frame that lands in the cache after the flush ran gets stuck there
        # and starves the drain loop. The target is baseline + the expected
        # data-segment count — see the derivations above.
        def rssi_open():
            return client_rssi.getOpen()

        wait_for_progress(
            lambda: out_of_order.cnt,
            baseline_segments + expected_segments,
            label=f"reorder settle Ver={version} Jumbo={jumbo}",
            health_check=rssi_open,
        )

        out_of_order.period = 0

        wait_for_progress(
            lambda: prbs_rx.getRxCount(),
            FRAME_COUNT,
            label=f"frame drain Ver={version} Jumbo={jumbo}",
            health_check=rssi_open,
        )

        # Enforce exact equality — wait_for_progress returns on >=, so this
        # catches any duplicated or replayed frames that would otherwise pass.
        assert prbs_rx.getRxCount() == FRAME_COUNT
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
        if client_started:
            try:
                client_rssi._stop()
            except Exception:
                pass
        if server_started:
            try:
                server_rssi._stop()
            except Exception:
                pass
        time.sleep(TEARDOWN_SETTLE_DELAY)

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
