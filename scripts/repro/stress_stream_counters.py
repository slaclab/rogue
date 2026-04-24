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
  - STREAM-006
  - STREAM-007
  - STREAM-008
  - HW-CORE-019

Stress non-atomic counter reads vs concurrent increments across:
  - STREAM-006 : Slave frameCount_ / frameBytes_ concurrent increment
  - STREAM-007 : Pool getAllocBytes / getAllocCount lock-free read vs
                 alloc/return under mtx_
  - STREAM-008 : RateDrop dropCount_ / nextPeriod_ / timePeriod_ concurrent
                 update
  - HW-CORE-019 : StreamWriterChannel getFrameCount() lock-free read

Pattern: multiple Master threads feed frames through the same target
(Slave / Pool / RateDrop / StreamWriterChannel); a separate polling thread
reads the getter APIs. TSan flags the non-atomic counter read.
"""
import threading

import pytest
import rogue

pytestmark = pytest.mark.repro


def _make_frame(master, size):
    frame = master._reqFrame(size, True)
    buf = bytearray(size)
    frame._write(buf, 0)
    return frame


@pytest.mark.repro
def test_stress_slave_frame_counter(stress_iters):
    """Slave frameCount_/frameBytes_ concurrent increment vs getFrameCount read (STREAM-006)."""
    errors = []

    master = rogue.interfaces.stream.Master()
    slave = rogue.interfaces.stream.Slave()
    master._setSlave(slave)

    def pusher():
        for _ in range(stress_iters // 10):
            try:
                f = _make_frame(master, 64)
                master._sendFrame(f)
            except Exception as e:
                errors.append(e)

    def poller():
        for _ in range(stress_iters // 10):
            try:
                _ = slave.getFrameCount()
                _ = slave.getByteCount()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=pusher) for _ in range(5)]
    threads += [threading.Thread(target=poller) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Slave counter stress errors: {errors}"


@pytest.mark.repro
def test_stress_pool_alloc_counter(stress_iters):
    """Pool getAllocBytes/getAllocCount lock-free read vs alloc/return (STREAM-007)."""
    errors = []

    pool = rogue.interfaces.stream.Pool()

    def allocator():
        for _ in range(stress_iters // 10):
            try:
                buf = pool._allocBuffer(1024, None)
                del buf  # returns buffer to pool
            except Exception as e:
                errors.append(e)

    def poller():
        for _ in range(stress_iters // 10):
            try:
                _ = pool.getAllocBytes()
                _ = pool.getAllocCount()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=allocator) for _ in range(5)]
    threads += [threading.Thread(target=poller) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Pool counter stress errors: {errors}"


@pytest.mark.repro
def test_stress_ratedrop_counter(stress_iters):
    """RateDrop dropCount_/nextPeriod_/timePeriod_ concurrent update (STREAM-008)."""
    errors = []

    master = rogue.interfaces.stream.Master()
    ratedrop = rogue.interfaces.stream.RateDrop(True, 0.001)  # period, drop beyond
    slave = rogue.interfaces.stream.Slave()
    master._setSlave(ratedrop)
    ratedrop._setSlave(slave)

    def pusher():
        for _ in range(stress_iters // 10):
            try:
                f = _make_frame(master, 32)
                master._sendFrame(f)
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=pusher) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"RateDrop counter stress errors: {errors}"


@pytest.mark.repro
def test_stress_streamwriterchannel_counter(stress_iters, tmp_path):
    """StreamWriterChannel getFrameCount() lock-free read (HW-CORE-019)."""
    errors = []

    writer = rogue.utilities.fileio.StreamWriter()
    writer.open(str(tmp_path / "stress_swc.dat"))
    ch = writer.getChannel(0)

    master = rogue.interfaces.stream.Master()
    master._setSlave(ch)

    def pusher():
        for _ in range(stress_iters // 10):
            try:
                f = _make_frame(master, 64)
                master._sendFrame(f)
            except Exception as e:
                errors.append(e)

    def poller():
        for _ in range(stress_iters // 10):
            try:
                _ = ch.getFrameCount()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=pusher) for _ in range(5)]
    threads += [threading.Thread(target=poller) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    writer.close()
    assert not errors, f"StreamWriterChannel counter stress errors: {errors}"
