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
import threading
import time
import warnings

import rogue
import rogue.interfaces.stream
import rogue.protocols.udp
import rogue.protocols.rssi
import rogue.utilities
import pytest

from conftest import wait_for


class FrameCounter(rogue.interfaces.stream.Slave):
    """Counts received frames and validates per-frame payload size.

    Used in concurrent-sender tests where interleaved Prbs streams
    cannot be validated by a single Prbs checker.  Tracks a per-size
    histogram so cross-sender substitutions surface as bucket shifts.

    `expected_sizes`: int, set of ints, or None (accept any size).
    """

    def __init__(self, expected_sizes=None):
        rogue.interfaces.stream.Slave.__init__(self)
        self._lock = threading.Lock()
        self._cnt = 0
        if isinstance(expected_sizes, int):
            self._expected_sizes = {expected_sizes}
        else:
            self._expected_sizes = expected_sizes
        self._size_counts = {}
        self.errors = []

    @property
    def count(self):
        with self._lock:
            return self._cnt

    @property
    def size_counts(self):
        with self._lock:
            return dict(self._size_counts)

    def _acceptFrame(self, frame):
        with frame.lock():
            size = frame.getPayload()
        with self._lock:
            self._cnt += 1
            self._size_counts[size] = self._size_counts.get(size, 0) + 1
            if self._expected_sizes is not None and size not in self._expected_sizes:
                self.errors.append(
                    f"size mismatch: got {size}, "
                    f"expected one of {sorted(self._expected_sizes)}"
                )

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
# Bound so a wedged sender surfaces as a failed assertion, not a stuck worker.
SENDER_JOIN_TIMEOUT = 30.0


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


def test_rssi_concurrent_senders_under_backpressure():
    # Exercises the merged wait+reserve critical section in applicationRx()
    # under contention.  Multiple senders with a tight outstanding window
    # ensures the curMaxBuffers_ check and txListCount_++ race on nearly
    # every frame.  Each sender uses a unique frame size so cross-sender
    # substitutions surface in the per-size histogram.
    udpSrv = rogue.protocols.udp.Server(0, True)
    port = udpSrv.getPort()
    udpCli = rogue.protocols.udp.Client("127.0.0.1", port, True)

    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiCli = rogue.protocols.rssi.Client(1400)

    # Tight window forces backpressure; 4 (not 2) keeps cum-ACK alive.
    rssiSrv.setLocMaxBuffers(4)
    rssiCli.setLocMaxBuffers(4)
    rssiSrv.setLocRetranTout(200)
    rssiCli.setLocRetranTout(200)

    udpSrv == rssiSrv.transport()
    udpCli == rssiCli.transport()

    n_senders = 4
    frames_per_sender = 25
    total = n_senders * frames_per_sender
    # Unique per-sender sizes (multiples of 4, >= 12) for histogram validation.
    sender_sizes = [128, 132, 136, 140]
    assert len(sender_sizes) == n_senders
    assert len(set(sender_sizes)) == n_senders, "sender sizes must be unique"

    prbsTxs = [rogue.utilities.Prbs() for _ in range(n_senders)]
    rxCounter = FrameCounter(expected_sizes=set(sender_sizes))

    for prbs in prbsTxs:
        rssiCli.application() << prbs
    rxCounter << rssiSrv.application()

    rssiSrv._start()
    rssiCli._start()
    threads = []

    try:
        assert wait_for(
            lambda: rssiCli.getOpen() and rssiSrv.getOpen(),
            timeout=CONNECTION_TIMEOUT
        ), "RSSI link did not open"

        sender_errors = []
        sender_errors_lock = threading.Lock()

        def sender(prbs, size):
            try:
                for _ in range(frames_per_sender):
                    prbs.genFrame(size)
            except BaseException as e:  # noqa: BLE001
                with sender_errors_lock:
                    sender_errors.append(e)

        threads = [
            threading.Thread(target=sender, args=(p, s))
            for p, s in zip(prbsTxs, sender_sizes)
        ]
        for t in threads:
            t.start()
        deadline = time.monotonic() + SENDER_JOIN_TIMEOUT
        for t in threads:
            t.join(timeout=max(0.0, deadline - time.monotonic()))
        for t in threads:
            assert not t.is_alive(), (
                f"sender did not complete within {SENDER_JOIN_TIMEOUT:.1f}s"
            )
        assert sender_errors == [], (
            f"sender thread raised unexpectedly: {sender_errors[:3]}"
        )

        wait_for_progress(lambda: rxCounter.count, total, "concurrent RSSI RX")
        assert rxCounter.count == total, (
            f"unexpected RX count: got {rxCounter.count}, expected {total}"
        )
        assert rssiCli.getDropCount() == 0
        assert rssiSrv.getDropCount() == 0
        assert rssiCli.getRetranCount() == 0, (
            f"unexpected retransmit on UDP loopback: {rssiCli.getRetranCount()}"
        )
        assert rssiSrv.getRetranCount() == 0, (
            f"unexpected retransmit on UDP loopback: {rssiSrv.getRetranCount()}"
        )
        assert rxCounter.errors == [], (
            f"frame integrity errors: {rxCounter.errors[:5]}"
        )
        size_counts = rxCounter.size_counts
        for size in sender_sizes:
            assert size_counts.get(size, 0) == frames_per_sender, (
                f"per-sender frame count mismatch: got {size_counts}, "
                f"expected {frames_per_sender} of each {sorted(sender_sizes)}"
            )
    finally:
        rssiCli._stop()
        rssiSrv._stop()
        # Cleanup join for threads that outlived the assertions.
        deadline = time.monotonic() + SENDER_JOIN_TIMEOUT
        for t in threads:
            if t.is_alive():
                t.join(timeout=max(0.0, deadline - time.monotonic()))
        leaked = [t.name for t in threads if t.is_alive()]
        if leaked:
            warnings.warn(
                f"sender thread(s) still alive after cleanup join: {leaked}; "
                "wait+reserve path may have regressed",
                stacklevel=2,
            )


def test_rssi_reset_wakes_blocked_senders():
    # Regression: stateError() must set state_ = StClosed BEFORE the reset
    # frame so txCond_ wakes see !StOpen.  Verifies that backpressured
    # senders unblock and exit cleanly when the peer resets mid-flight.
    udpSrv = rogue.protocols.udp.Server(0, True)
    port = udpSrv.getPort()
    udpCli = rogue.protocols.udp.Client("127.0.0.1", port, True)

    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiCli = rogue.protocols.rssi.Client(1400)

    rssiSrv.setLocMaxBuffers(4)
    rssiCli.setLocMaxBuffers(4)
    rssiSrv.setLocRetranTout(200)
    rssiCli.setLocRetranTout(200)

    udpSrv == rssiSrv.transport()
    udpCli == rssiCli.transport()

    n_senders = 8
    frames_per_sender = 200
    total = n_senders * frames_per_sender

    prbsTxs = [rogue.utilities.Prbs() for _ in range(n_senders)]
    rxCounter = FrameCounter()

    for prbs in prbsTxs:
        rssiCli.application() << prbs
    rxCounter << rssiSrv.application()

    rssiSrv._start()
    rssiCli._start()
    server_stopped = False
    threads = []

    try:
        assert wait_for(
            lambda: rssiCli.getOpen() and rssiSrv.getOpen(),
            timeout=CONNECTION_TIMEOUT
        ), "RSSI link did not open"

        sender_errors = []
        sender_errors_lock = threading.Lock()
        # frames_pushed: completion count.  in_genFrame: proves sender
        # is inside genFrame (i.e. backpressured) at the moment of reset.
        frames_pushed_lock = threading.Lock()
        frames_pushed = [0]
        in_genFrame_lock = threading.Lock()
        in_genFrame = [0]

        def sender(prbs):
            try:
                for _ in range(frames_per_sender):
                    with in_genFrame_lock:
                        in_genFrame[0] += 1
                    try:
                        prbs.genFrame(128)
                        with frames_pushed_lock:
                            frames_pushed[0] += 1
                    finally:
                        with in_genFrame_lock:
                            in_genFrame[0] -= 1
            except BaseException as e:  # noqa: BLE001
                with sender_errors_lock:
                    sender_errors.append(e)

        threads = [
            threading.Thread(target=sender, args=(p,))
            for p in prbsTxs
        ]
        for t in threads:
            t.start()

        # Precondition: senders are actually backpressured when we reset.
        def precondition():
            if rxCounter.count == 0:
                return False
            with frames_pushed_lock:
                if frames_pushed[0] >= total:
                    return False
            with in_genFrame_lock:
                return in_genFrame[0] > 0

        assert wait_for(
            precondition,
            timeout=CONNECTION_TIMEOUT
        ), "no sender inside applicationRx() before reset"

        with frames_pushed_lock:
            pushed_at_reset = frames_pushed[0]
        with in_genFrame_lock:
            in_gen_at_reset = in_genFrame[0]

        rssiSrv._stop()
        server_stopped = True

        assert pushed_at_reset < total, (
            f"senders drained before reset (pushed={pushed_at_reset}/{total}); "
            "tight window did not produce backpressure on this runner -- "
            "close-before-notify path is not being exercised"
        )
        assert in_gen_at_reset > 0, (
            "no sender was inside genFrame() at the moment of reset "
            f"(pushed={pushed_at_reset}/{total}); close-before-notify "
            "path is not being exercised"
        )

        deadline = time.monotonic() + SENDER_JOIN_TIMEOUT
        for t in threads:
            t.join(timeout=max(0.0, deadline - time.monotonic()))
        for t in threads:
            assert not t.is_alive(), (
                "sender did not wake after peer reset; close-before-notify "
                "may have regressed"
            )
        assert sender_errors == [], (
            f"sender thread raised unexpectedly during reset: "
            f"{sender_errors[:3]}"
        )

        assert wait_for(
            lambda: not rssiCli.getOpen(),
            timeout=CONNECTION_TIMEOUT
        ), "client did not observe link close after peer reset"
    finally:
        rssiCli._stop()
        if not server_stopped:
            rssiSrv._stop()
        # Cleanup join for threads that outlived the assertions.
        deadline = time.monotonic() + SENDER_JOIN_TIMEOUT
        for t in threads:
            if t.is_alive():
                t.join(timeout=max(0.0, deadline - time.monotonic()))
        leaked = [t.name for t in threads if t.is_alive()]
        if leaked:
            warnings.warn(
                f"sender thread(s) still alive after cleanup join: {leaked}; "
                "wake-on-reset path may have regressed",
                stacklevel=2,
            )


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


def test_rssi_double_stop_is_idempotent():
    # Regression: stop() must be idempotent -- Python destructors call it
    # again at scope exit after explicit _stop().  Without thread_.reset()
    # the second join() would std::terminate().
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
        # Three back-to-back calls must be no-ops after the first join.
        rssiCli._stop()
        rssiCli._stop()
        rssiCli._stop()
        rssiSrv._stop()
        rssiSrv._stop()
        rssiSrv._stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
