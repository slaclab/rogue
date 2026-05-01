#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
"""Thread-safety tests for rogue.interfaces.stream.Pool allocation counters.

Pool.getAllocBytes() and Pool.getAllocCount() read without holding the
pool mutex, while retBuffer / allocBuffer / decCounter modify under lock.
This test hammers concurrent alloc/free to surface torn reads.
"""
import threading
import time
import rogue.interfaces.stream as ris


class Source(ris.Master):
    pass


class Sink(ris.Slave):
    def _acceptFrame(self, frame):
        pass


def _alloc_free_loop(master, size, iterations, errors):
    """Allocate and immediately release frames in a tight loop."""
    try:
        for _ in range(iterations):
            frame = master._reqFrame(size, True)
            del frame
    except Exception as e:
        errors.append(e)


def test_pool_alloc_bytes_no_negative():
    """getAllocBytes() must never go negative under concurrent alloc/free."""
    sink = Sink()
    masters = []
    for _ in range(4):
        m = Source()
        m >> sink
        masters.append(m)

    errors = []
    stop = threading.Event()
    observed_negative = []

    iterations = 2000
    buf_size = 64

    def monitor():
        while not stop.is_set():
            val = sink.getAllocBytes()
            if val > 2**31:
                observed_negative.append(val)
            time.sleep(0.0001)

    mon = threading.Thread(target=monitor, daemon=True)
    mon.start()

    threads = []
    for m in masters:
        t = threading.Thread(target=_alloc_free_loop, args=(m, buf_size, iterations, errors), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=30)

    stop.set()
    mon.join(timeout=2)
    assert not mon.is_alive(), "monitor thread hung"

    for t in threads:
        assert not t.is_alive(), "alloc/free worker hung"

    assert not errors, f"Worker errors: {errors}"
    assert sink.getAllocBytes() == 0, f"Leak: {sink.getAllocBytes()} bytes still allocated"
    assert sink.getAllocCount() == 0, f"Leak: {sink.getAllocCount()} buffers still allocated"
    assert not observed_negative, f"Observed negative alloc bytes (torn read): {observed_negative[:5]}"


def test_pool_alloc_count_consistency():
    """getAllocCount() must equal the number of outstanding buffers."""
    sink = Sink()
    masters = []
    for _ in range(4):
        m = Source()
        m >> sink
        masters.append(m)

    errors = []
    iterations = 1000
    buf_size = 128

    threads = []
    for m in masters:
        t = threading.Thread(target=_alloc_free_loop, args=(m, buf_size, iterations, errors), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=30)

    for t in threads:
        assert not t.is_alive(), "alloc/free worker hung"

    assert not errors, f"Worker errors: {errors}"
    assert sink.getAllocBytes() == 0
    assert sink.getAllocCount() == 0
