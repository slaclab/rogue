#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
# Regression for the unbounded-`waitOnUpdate()` hang reported by SO/LAT
# rogue 6 deployments. The user pattern was:
#
#     with self.root.updateGroup():
#         self.root.waitOnUpdate()
#
# `waitOnUpdate()` previously called `_updateQueue.join()`, which only
# returns when the queue's unfinished-task counter reaches zero. Under
# sustained producer load (poll thread, listener-fired sets, UDP
# listeners) the counter never settles at zero, so the wait could
# silently take >2 minutes and trip the ZMQ client linkTimeout.
#
# The fix changes `waitOnUpdate()` to a bounded barrier: an Event sentinel
# is appended to the queue and the call returns the moment the worker
# reaches it. Items added during the wait are NOT included.
#-----------------------------------------------------------------------------

import threading
import time

import pyrogue as pr


class _VarRoot(pr.Root):
    def __init__(self):
        super().__init__(name="root", pollEn=False)
        for i in range(8):
            self.add(pr.LocalVariable(name=f"V{i}", value=0))


def _spawn_set_producer(root, var_name, stop_event):
    # Hammer var.set() from a background thread. Each set() with the
    # default `write=True` runs through LocalBlock._checkTransaction()
    # and queues a notification on the update worker, mirroring what
    # the SO pysmurf-monitor pipeline sees from polled hardware
    # variables and listener-fired updates.
    def producer():
        v = getattr(root, var_name)
        i = 0
        while not stop_event.is_set():
            v.set(i)
            i += 1

    t = threading.Thread(target=producer, daemon=True)
    t.start()
    return t


def test_wait_on_update_returns_promptly_with_idle_queue():
    # Sanity: with no producer, waitOnUpdate returns essentially immediately.
    with _VarRoot() as root:
        t0 = time.monotonic()
        root.waitOnUpdate()
        assert time.monotonic() - t0 < 1.0


def test_wait_on_update_bounded_under_concurrent_producer():
    # Reproduces the >2 minute hang. With the bounded-barrier fix, the
    # call returns within a small bounded time even though another thread
    # keeps queueing variable updates the entire time.
    with _VarRoot() as root:
        stop = threading.Event()
        producer = _spawn_set_producer(root, "V0", stop)

        try:
            # Let the producer get rolling so the queue is non-empty.
            time.sleep(0.1)

            t0 = time.monotonic()
            root.waitOnUpdate()
            elapsed = time.monotonic() - t0

            # 5 s is generous — the actual barrier-drain is sub-second on a
            # quiet machine. Hangs from the old `Queue.join()` behavior
            # would blow well past this.
            assert elapsed < 5.0, f"waitOnUpdate took {elapsed:.2f}s"
        finally:
            stop.set()
            producer.join(timeout=2.0)


def test_wait_on_update_inside_update_group_bounded():
    # Tristan's exact pattern: waitOnUpdate() inside updateGroup() must
    # also be bounded under concurrent producer load.
    with _VarRoot() as root:
        stop = threading.Event()
        producer = _spawn_set_producer(root, "V1", stop)

        try:
            time.sleep(0.1)

            t0 = time.monotonic()
            with root.updateGroup():
                root.waitOnUpdate()
            elapsed = time.monotonic() - t0

            assert elapsed < 5.0, (
                f"waitOnUpdate inside updateGroup took {elapsed:.2f}s"
            )
        finally:
            stop.set()
            producer.join(timeout=2.0)


def test_wait_on_update_bounded_under_listener_self_storm():
    # The "indeterminate loop" Tristan was worried about: a varListener
    # that re-fires the *same* variable from the worker thread, so each
    # callback queues another update before task_done() can complete.
    # Without the bounded-barrier fix, Queue.join()'s unfinished-task
    # counter never settles to zero and the call hangs.
    with _VarRoot() as root:
        stop_listener = threading.Event()
        kick_count = [0]
        kick_lock = threading.Lock()

        def listener(path, value):
            with kick_lock:
                if path.endswith(".V2") and not stop_listener.is_set():
                    kick_count[0] += 1
                    # Re-fire the same variable from the worker thread.
                    # This satisfies the listener condition again on the
                    # next callback, producing an unbounded self-storm
                    # until stop_listener is set.
                    root.V2.set(kick_count[0])

        root.addVarListener(listener)

        try:
            # Prime the chain and let the listener-driven storm get rolling.
            root.V2.set(1)
            time.sleep(0.1)

            t0 = time.monotonic()
            root.waitOnUpdate()
            elapsed = time.monotonic() - t0

            assert elapsed < 5.0, f"waitOnUpdate under listener self-storm took {elapsed:.2f}s"
        finally:
            # Stop the self-storm so Root.stop() can drain cleanly.
            stop_listener.set()


def test_wait_on_update_drains_pending_listener_callbacks():
    # The whole point of waitOnUpdate is that, after it returns, items
    # queued before the call have actually fired their root listeners.
    # Verify that contract still holds with the bounded-barrier
    # implementation.
    with _VarRoot() as root:
        seen = []
        seen_lock = threading.Lock()

        def listener(path, value):
            with seen_lock:
                seen.append((path, value.value))

        root.addVarListener(listener)

        with root.updateGroup():
            root.V4.set(42)
            root.V5.set(43)

        # Without waitOnUpdate the worker may not have processed the batch
        # yet. After waitOnUpdate, the pre-queue updates must be visible.
        root.waitOnUpdate()

        with seen_lock:
            seen_map = {p: v for p, v in seen}

        assert seen_map.get("root.V4") == 42
        assert seen_map.get("root.V5") == 43
