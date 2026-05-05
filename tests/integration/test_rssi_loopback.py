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
    """Minimal Slave that counts received frames and tracks per-frame
    payload size.  Used in concurrent-sender tests where a single Prbs
    checker cannot validate interleaved sequences (it tracks one rxSeq_),
    but where we still want stronger evidence than a raw count: a frame
    that arrives truncated, padded, or split would land here with a
    different size and surface as a content error rather than a count
    mismatch.  Drops/duplicates from a slot-reservation race are picked
    up by the per-RSSI dropCount/retranCount asserts in callers.

    `expected_sizes` may be a single int (one valid size), a set of
    ints (multiple valid sizes, used when each sender writes a unique
    size), or None to accept any size.  When a set is given, the
    receive-side per-size histogram (`size_counts`) lets callers
    detect a cross-sender substitution that preserves the total count
    and the size of each individual frame: a substitution would shift
    one bucket up and another down even though the sum is unchanged.
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
# Bound on per-sender thread completion in concurrent tests.  A wedged
# sender (e.g. a regression that breaks the txCond_ wake path) must
# surface as a failed assertion, not a stuck pytest worker.
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
    # Drive multiple application senders concurrently with a tight outstanding
    # window so applicationRx() backpressure (txMtx_/txCond_ wait) and the
    # slot-reserving txListCount_++ (transportTxLocked) execute under
    # contention on nearly every frame.  This exercises the merged
    # wait+reserve critical section: if it ever regressed to a separate
    # observe-then-reserve pair, two senders waking on a single freed slot
    # would both pass the curMaxBuffers_ check and both increment
    # txListCount_, overshooting the negotiated outstanding-window limit
    # and corrupting the txList_/lastAckRx_ ring.
    #
    # One Prbs source per thread so per-source pMtx_ does NOT serialize
    # genFrame(); the senders genuinely race into Application::acceptFrame
    # -> Controller::applicationRx().  We can't validate Prbs sequences on
    # the receive side because multiple interleaved Prbs streams would
    # each look like a sequence error to a single Prbs checker (it tracks
    # one rxSeq_), and a Python Master subclass cannot be used here either
    # (RSSI's GilRelease in applicationRx is not safe with concurrent
    # Python-thread invocations of _sendFrame).  And every fresh
    # `rogue.utilities.Prbs()` starts at txSeq_=0 with the same LFSR
    # seed, so the payload bytes that two senders emit for their first
    # frame are identical: a single `expected_size` check could not
    # distinguish a frame produced by sender A from one produced by
    # sender B if a corrupted txList_ slot delivered the wrong source's
    # payload at the same nominal size.  We close that gap by giving
    # each sender a UNIQUE frame size (all multiples of byteWidth_=4
    # and >= minSize_=12 so Prbs::genFrame accepts them) and asserting
    # that each size arrives exactly frames_per_sender times.  A
    # cross-sender substitution caused by a contended slot would shift
    # one per-size bucket up and another down while leaving the sum at
    # TOTAL.  Together with the four RSSI-internal signals below this
    # exercises content integrity under contention without depending
    # on a Prbs checker that can't see interleaved streams:
    #   - frame count must be exactly TOTAL (drops bypass dropCount)
    #   - dropCount on either side > 0 indicates corrupted/lost frames
    #   - retranCount > 0 indicates a missed-ack from a duplicated slot
    #   - per-frame size must equal the bytes the sender wrote (catches
    #     truncation or padding of payloads stored in a contended slot)
    #   - per-size frame count == frames_per_sender (catches a cross-
    #     sender substitution that preserves total count and frame size)
    udpSrv = rogue.protocols.udp.Server(0, True)
    port = udpSrv.getPort()
    udpCli = rogue.protocols.udp.Client("127.0.0.1", port, True)

    rssiSrv = rogue.protocols.rssi.Server(1400)
    rssiCli = rogue.protocols.rssi.Client(1400)

    # Tight transmit window so every frame sees backpressure: the
    # wait+reserve critical section runs under contention on (nearly)
    # every send.  4 buffers (rather than 2) keeps the cumulative-ACK
    # logic alive -- with 2 buffers the receiver hits the max-cum-ACK
    # threshold of 2 only after every other frame, which under loaded
    # CI runners stalls before the senders drain.
    rssiSrv.setLocMaxBuffers(4)
    rssiCli.setLocMaxBuffers(4)
    # Match the long retransmit timeout used in the clean-path test so
    # ACK delivery jitter under pytest-xdist does not flag spurious drops.
    rssiSrv.setLocRetranTout(200)
    rssiCli.setLocRetranTout(200)

    udpSrv == rssiSrv.transport()
    udpCli == rssiCli.transport()

    n_senders = 4
    frames_per_sender = 25
    total = n_senders * frames_per_sender
    # Distinct per-sender frame sizes (multiples of byteWidth_=4, all
    # >= minSize_=12, all small enough to fit in one RSSI segment) so
    # cross-sender substitutions surface in the per-size histogram.
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

        # Capture per-thread exceptions so a regression that starts
        # raising inside genFrame() (e.g. a corrupted slot reservation
        # raising in Controller::applicationRx) surfaces as an assertion
        # below instead of pytest silently emitting an "exception in
        # thread" warning while the bounded-join + !is_alive() check
        # still passes -- matches the pattern used in the reset test.
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
        # Bound joins so a wedged sender surfaces as an assertion rather
        # than a stuck pytest worker (matches the pattern used in
        # tests/integration/test_init_read_timeout_integration.py).
        deadline = time.monotonic() + SENDER_JOIN_TIMEOUT
        for t in threads:
            t.join(timeout=max(0.0, deadline - time.monotonic()))
        for t in threads:
            assert not t.is_alive(), (
                f"sender did not complete within {SENDER_JOIN_TIMEOUT:.1f}s"
            )
        # Surface any exception raised inside a sender thread.  An early
        # exit via raise would otherwise satisfy the !is_alive() check
        # above and mask a regression on the concurrent-send path.
        assert sender_errors == [], (
            f"sender thread raised unexpectedly: {sender_errors[:3]}"
        )

        wait_for_progress(lambda: rxCounter.count, total, "concurrent RSSI RX")
        # Enforce exact equality — wait_for_progress returns on >=, so an
        # exact-count check is needed to catch a duplicated/replayed frame
        # that a wait+reserve race could surface as a double-delivered slot
        # without changing the >=total wake.  Mirrors the pattern in
        # tests/integration/test_udp_packetizer_integration.py:260-262.
        assert rxCounter.count == total, (
            f"unexpected RX count: got {rxCounter.count}, expected {total}"
        )
        assert rssiCli.getDropCount() == 0
        assert rssiSrv.getDropCount() == 0
        # A duplicated/overwritten slot caused by a wait+reserve regression
        # would manifest as a missed cumulative ack and force the sender
        # into retransmission; UDP loopback otherwise has no loss source.
        assert rssiCli.getRetranCount() == 0, (
            f"unexpected retransmit on UDP loopback: {rssiCli.getRetranCount()}"
        )
        assert rssiSrv.getRetranCount() == 0, (
            f"unexpected retransmit on UDP loopback: {rssiSrv.getRetranCount()}"
        )
        # Per-frame size validation in FrameCounter catches mid-frame
        # corruption that would not change the receive count.
        assert rxCounter.errors == [], (
            f"frame integrity errors: {rxCounter.errors[:5]}"
        )
        # Per-sender frame count: each sender used a unique size, so a
        # healthy slot-reservation path delivers exactly
        # frames_per_sender frames at each size.  A wait+reserve
        # regression that swapped one sender's frame for another's
        # would shift one per-size bucket up and another down while
        # leaving the sum at TOTAL, so this is strictly stronger than
        # the rxCounter.count == total check above.
        size_counts = rxCounter.size_counts
        for size in sender_sizes:
            assert size_counts.get(size, 0) == frames_per_sender, (
                f"per-sender frame count mismatch: got {size_counts}, "
                f"expected {frames_per_sender} of each {sorted(sender_sizes)}"
            )
    finally:
        rssiCli._stop()
        rssiSrv._stop()
        # Defensive bounded join: if a post-join assertion above (e.g.
        # !is_alive(), exact-count, dropCount/retranCount, or per-frame
        # size) raised, the non-daemon sender threads would otherwise
        # outlive the test and execute against already-stopped RSSI
        # objects.  Only join threads still alive; the success path has
        # already joined them.
        deadline = time.monotonic() + SENDER_JOIN_TIMEOUT
        for t in threads:
            if t.is_alive():
                t.join(timeout=max(0.0, deadline - time.monotonic()))
        # If a sender is genuinely wedged (regression in the wait+reserve
        # path) the bounded join above will time out without killing the
        # thread.  Python cannot force-cancel a thread, so the best we can
        # do is surface a warning so the leak is visible alongside the
        # original assertion instead of letting a non-daemon worker hang
        # the rest of the pytest session silently.
        leaked = [t.name for t in threads if t.is_alive()]
        if leaked:
            warnings.warn(
                f"sender thread(s) still alive after cleanup join: {leaked}; "
                "wait+reserve path may have regressed",
                stacklevel=2,
            )


def test_rssi_reset_wakes_blocked_senders():
    # Regression: stateError() must mark state_ = StClosed *before* sending
    # the reset frame, so the txCond_.notify_all() that wakes blocked
    # applicationRx() backpressure waiters fires after the close transition
    # has been published.  Without that ordering a waiter could wake on the
    # notify, observe state_ == StOpen plus a freshly-reset txListCount_,
    # and emit a payload onto the link being reset.
    #
    # Drive the path:
    #   - open RSSI link with a tight outstanding window
    #   - launch concurrent senders that saturate the window
    #   - while senders are still pushing frames, _stop() the peer so the
    #     client receives a rst and its stateError() runs against in-flight
    #     senders (some of which are in the txMtx_/txCond_ wait at the
    #     moment of reset)
    #   - assert every sender thread exits within a bounded join, so a
    #     wedge surfaces as an assertion rather than a stuck pytest worker
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

        # Capture per-thread exceptions so an unexpected failure inside
        # genFrame() (e.g. a regression that makes the sender side raise
        # during reset) surfaces as an assertion below instead of pytest
        # silently emitting an "exception in thread" warning while the
        # bounded join still succeeds.
        sender_errors = []
        sender_errors_lock = threading.Lock()
        # Track per-sender push completion AND in-flight genFrame()
        # entries so the precondition below can prove the senders are
        # actually backpressured at the moment of reset, not merely
        # "still have frames left in their for-loops".  Two counters
        # are needed:
        #   - frames_pushed: incremented after genFrame() returns.
        #     frames_pushed < total proves at least one sender has not
        #     yet completed its full loop, but does not prove a sender
        #     is currently inside genFrame -- the last frame may have
        #     been handed off and even fully received while the post-
        #     genFrame increment is still pending.
        #   - in_genFrame: incremented BEFORE genFrame and decremented
        #     in finally AFTER it returns.  in_genFrame > 0 proves at
        #     least one sender is currently inside Prbs::genFrame().
        #
        # in_genFrame is a tight upper bound on "sender inside
        # Application::acceptFrame -> Controller::applicationRx", but it
        # is NOT a strict equivalence: Prbs::genFrame's post-sendFrame
        # tail (txSeq_++, txCount_++, txBytes_+=size, optional
        # updateTime() in Prbs.cpp:394-406) runs after sendFrame()
        # returns but before genFrame() does, so in_genFrame can be
        # briefly true while the sender has already left applicationRx.
        # The tail is a handful of integer increments plus an
        # updateTime() that only does meaningful work once per second,
        # so its duration is < 1 us in steady state versus millisecond-
        # scale backpressure waits inside applicationRx -- the
        # probability that all senders are simultaneously in the post-
        # sendFrame tail (vs. any inside applicationRx) at a polled
        # instant is negligible with 8 senders on a 4-buffer window.
        # A strict bracket would have to wrap _sendFrame on a Python
        # Master per thread, but Boost.Python's _sendFrame binding
        # crashes from a non-main Python thread with "PyThreadState_Get:
        # GIL is released" -- the same constraint already documented in
        # test_rssi_concurrent_senders_under_backpressure above.  Note
        # that the regression detector for the close-before-notify
        # ordering is the bounded-join + sender_errors check AFTER
        # rssiSrv._stop(), not the precondition; this counter is a
        # confidence check that prevents the test from silently
        # degrading into a shutdown smoke test on a fast runner.
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

        # Bounded joins below already guarantee these threads do not
        # outlive the test; daemon=True would let a wedged worker linger
        # against already-stopped RSSI objects on assertion failure.
        threads = [
            threading.Thread(target=sender, args=(p,))
            for p in prbsTxs
        ]
        for t in threads:
            t.start()

        # Verify the precondition: senders are actually backpressured at
        # the moment we yank the peer.  Without this check the test would
        # silently degrade into an ordinary shutdown test on a fast runner
        # if 1600 frames drained before the wait expired -- the
        # close-before-notify path this test is meant to lock in would
        # never run.
        #
        # The check has three parts:
        #   - rxCounter.count > 0 proves the link is up and senders are
        #     actively flushing frames.
        #   - frames_pushed[0] < total proves at least one sender has
        #     not yet finished its for-loop.  Necessary but not
        #     sufficient on a fast runner: the last frame can have been
        #     handed off and even fully received while the post-genFrame
        #     increment is still pending.
        #   - in_genFrame[0] > 0 proves at least one sender is CURRENTLY
        #     inside Prbs::genFrame.  This is a tight upper bound on
        #     "currently inside Controller::applicationRx" (see the
        #     counter-definition comment above for the post-sendFrame
        #     tail caveat); without this the wait_for() could observe a
        #     stale frames_pushed[0] < total while every sender was
        #     between iterations.
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

        # Snapshot the in-flight counters as close to _stop() as
        # possible so the assertion message reflects what was true at
        # the instant we triggered the close path.  A small window
        # remains between the snapshot and rssiSrv._stop(), but on a
        # tight 4-buffer window with 8 senders pushing 1600 frames at
        # 128 bytes the senders are virtually always backpressured
        # there, and any flake would surface as in_gen_at_reset == 0
        # rather than as a silent skip.
        with frames_pushed_lock:
            pushed_at_reset = frames_pushed[0]
        with in_genFrame_lock:
            in_gen_at_reset = in_genFrame[0]

        # Now yank the peer.  rssiSrv._stop() runs Controller::stateError()
        # on its way out and emits rst, which the client receives and
        # processes via its own stateError() -- exactly the path under test.
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
        # Surface any exception raised inside a sender thread.  An early
        # exit via raise would otherwise satisfy the !is_alive() check
        # above and mask a regression on the wake-on-reset path.
        assert sender_errors == [], (
            f"sender thread raised unexpectedly during reset: "
            f"{sender_errors[:3]}"
        )

        assert wait_for(
            lambda: not rssiCli.getOpen(),
            timeout=CONNECTION_TIMEOUT
        ), "client did not observe link close after peer reset"
    finally:
        # Stop RSSI first so any sender still blocked in applicationRx()
        # backpressure wakes via stateError() before we try to join.
        rssiCli._stop()
        if not server_stopped:
            rssiSrv._stop()
        # Defensive bounded join: if a precondition assertion above
        # raised before the inline join ran, the non-daemon sender
        # threads would otherwise outlive the test and execute against
        # already-stopped RSSI objects.  Only join threads still alive;
        # the success path has already joined them.
        deadline = time.monotonic() + SENDER_JOIN_TIMEOUT
        for t in threads:
            if t.is_alive():
                t.join(timeout=max(0.0, deadline - time.monotonic()))
        # If a sender is genuinely wedged (regression in the wake-on-reset
        # path) the bounded join above will time out without killing the
        # thread.  Python cannot force-cancel a thread, so the best we can
        # do is surface a warning so the leak is visible alongside the
        # original assertion instead of letting a non-daemon worker hang
        # the rest of the pytest session silently.
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
    # Regression: rpr::Controller::stop() must be idempotent across
    # repeated calls.  The Python lifecycle exposes _stop() (= Client::stop
    # / Server::stop -> cntl_->stop), and Client/Server destructors then
    # call cntl_->stop() again at scope exit, so the second invocation is
    # part of the normal Python teardown path.  After the first call joins
    # the worker, Controller::stop() must clear thread_ so the next call
    # short-circuits via the if(thread_) guard; without thread_.reset(),
    # a second join() on an already-joined std::thread throws
    # std::system_error or invokes std::terminate().
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
        # First _stop() joins the worker and resets thread_; subsequent
        # calls must be no-ops.  An assertion-free run of three back-to-
        # back _stop() calls is the contract: any of join-on-joined,
        # double-reset, or notify-on-destroyed-condvar would surface as
        # an exception out of pybind/boost::python or as process abort.
        rssiCli._stop()
        rssiCli._stop()
        rssiCli._stop()
        rssiSrv._stop()
        rssiSrv._stop()
        rssiSrv._stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
