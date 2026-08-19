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
"""Behavioural coverage for the two performance-counter families no C++
doctest can reach: the Python-to-C++ GIL crossing counters (GilRelease and
ScopedGil bodies compile only when a Python interpreter is present) and the
Rogue-issued I/O call/byte counters (which require a real socket transport).

Also proves the transaction path's own honest reframing: a RemoteVariable
set against ``rogue.interfaces.memory.Emulate`` issues zero Rogue-issued I/O
calls, since Emulate is pure in-process C++ with no socket or ZeroMQ traffic.
"""

import pyrogue as pr
import rogue
import rogue.interfaces.memory
import rogue.interfaces.stream
import rogue.protocols.batcher
import rogue.utilities
import pytest

from conftest import wait_for


class _CounterDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add(pr.RemoteVariable(
            name      = 'Reg',
            offset    = 0x0,
            bitSize   = 32,
            bitOffset = 0,
            base      = pr.UInt,
            mode      = 'RW',
        ))


class _CounterRoot(pr.Root):
    def __init__(self):
        super().__init__(name='CounterRoot', timeout=2.0, pollEn=False)
        # Pure in-process memory emulator: no socket or ZeroMQ traffic is
        # ever issued servicing a transaction against it.
        self._mem = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(self._mem)
        self.add(_CounterDevice(name='Dev', offset=0x0, memBase=self._mem))


_TRANSACTION_GETTERS = (
    rogue.PerfCounters.getTransactionCreateCount,
    rogue.PerfCounters.getTransactionRequestCount,
    rogue.PerfCounters.getTransactionRequestBytes,
    rogue.PerfCounters.getTransactionLockCount,
    rogue.PerfCounters.getGilReleaseCount,
    rogue.PerfCounters.getGilAcquireCount,
)

# Restricted to the transaction-family counters for the repeat-determinism
# check below. gGilReleaseCount/gGilAcquireCount are process-wide and also
# incremented by Root's own background threads (independent of pollEn),
# so an exact-delta comparison across two back-to-back operations is
# inherently racy for that family; the "each counter increases" test above
# already covers them with a robust monotonic (>) check instead.
_DETERMINISTIC_GETTERS = (
    rogue.PerfCounters.getTransactionCreateCount,
    rogue.PerfCounters.getTransactionRequestCount,
    rogue.PerfCounters.getTransactionRequestBytes,
    rogue.PerfCounters.getTransactionLockCount,
)


def _snapshot(getters):
    return tuple(getter() for getter in getters)


def test_variable_set_against_emulate_raises_transaction_and_gil_counters():
    with _CounterRoot() as root:
        before = _snapshot(_TRANSACTION_GETTERS)

        root.Dev.Reg.set(0x1234)

        after = _snapshot(_TRANSACTION_GETTERS)

        for getter, beforeVal, afterVal in zip(_TRANSACTION_GETTERS, before, after):
            assert afterVal > beforeVal, f"{getter.__name__} did not increase: {beforeVal} -> {afterVal}"


def test_variable_set_against_emulate_leaves_io_call_count_at_a_recorded_zero_delta():
    with _CounterRoot() as root:
        before = rogue.PerfCounters.getIoCallCount()

        root.Dev.Reg.set(0x5A5A)

        after = rogue.PerfCounters.getIoCallCount()

        # The transaction path is structurally zero-I/O against Emulate.
        # This asserts the recorded zero explicitly rather than skipping the
        # case, since an omitted case would leave the claim unproven.
        assert after - before == 0


def test_repeated_variable_set_raises_deterministic_identical_deltas_each_time():
    with _CounterRoot() as root:
        def one_set_delta():
            before = _snapshot(_DETERMINISTIC_GETTERS)
            root.Dev.Reg.set(0x1)
            after = _snapshot(_DETERMINISTIC_GETTERS)
            return tuple(a - b for a, b in zip(after, before))

        first = one_set_delta()
        second = one_set_delta()

        assert all(delta > 0 for delta in first), first
        assert first == second, f"deltas differed across identical repeats: {first} vs {second}"


@pytest.mark.integration
def test_tcp_stream_pair_raises_io_call_and_byte_counters(free_tcp_port):
    serv = rogue.interfaces.stream.TcpServer("127.0.0.1", free_tcp_port)
    client = rogue.interfaces.stream.TcpClient("127.0.0.1", free_tcp_port)

    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()

    serv << prbsTx
    prbsRx << client

    prbsRx.checkPayload(True)

    callBefore = rogue.PerfCounters.getIoCallCount()
    bytesBefore = rogue.PerfCounters.getIoBytes()

    frameCount = 20
    frameSize = 500
    for _ in range(frameCount):
        prbsTx.genFrame(frameSize)

    assert wait_for(lambda: prbsRx.getRxCount() == frameCount, timeout=5.0)
    assert prbsRx.getRxErrors() == 0

    callDelta = rogue.PerfCounters.getIoCallCount() - callBefore
    bytesDelta = rogue.PerfCounters.getIoBytes() - bytesBefore

    assert callDelta > 0
    # The byte total must be at least the payload bytes the receiver reports:
    # every zmq_sendmsg/zmq_recvmsg call site also counts the smaller header
    # multipart messages, so the total is always >= the payload alone.
    assert bytesDelta >= prbsRx.getRxBytes()

    serv.close()
    client.close()


def test_slave_exposes_the_monotonic_pool_allocation_getters():
    sink = rogue.interfaces.stream.Slave()

    assert sink.getAllocTotalCount() == 0
    assert sink.getAllocTotalBytes() == 0
    assert sink.getAllocPeakBytes() == 0


@pytest.mark.integration
def test_prbs_into_a_bare_slave_sink_raises_the_monotonic_pool_allocation_totals():
    prbsTx = rogue.utilities.Prbs()
    sink = rogue.interfaces.stream.Slave()
    prbsTx >> sink

    frameCount = 20
    frameSize = 1000

    countBefore = sink.getAllocTotalCount()
    bytesBefore = sink.getAllocTotalBytes()

    for _ in range(frameCount):
        prbsTx.genFrame(frameSize)

    countDelta = sink.getAllocTotalCount() - countBefore
    bytesDelta = sink.getAllocTotalBytes() - bytesBefore

    assert countDelta >= frameCount
    assert bytesDelta >= frameCount * frameSize
    assert sink.getAllocPeakBytes() > 0


@pytest.mark.integration
def test_prbs_into_a_bare_slave_sink_raises_the_slave_frame_and_byte_counters():
    prbsTx = rogue.utilities.Prbs()
    sink = rogue.interfaces.stream.Slave()
    prbsTx >> sink

    frameCount = 20
    frameSize = 1000

    frameBefore = sink.getFrameCount()
    byteBefore = sink.getByteCount()

    for _ in range(frameCount):
        prbsTx.genFrame(frameSize)

    # The base Slave class runs its own acceptFrame here since sink is a
    # bare Slave with no _acceptFrame override, so these counters must
    # reflect exactly the frames just generated.
    assert sink.getFrameCount() - frameBefore == frameCount
    assert sink.getByteCount() - byteBefore == frameCount * frameSize


@pytest.mark.integration
def test_prbs_into_a_combiner_raises_the_queued_frame_count_until_send_batch_drains_it():
    prbsTx = rogue.utilities.Prbs()
    combiner = rogue.protocols.batcher.CombinerV2()
    sink = rogue.interfaces.stream.Slave()
    prbsTx >> combiner >> sink

    frameCount = 20
    frameSize = 1000

    # getCount() is a live queue-depth gauge (queue_.size()), not a cumulative counter, so
    # it reaches the generated count with no wait: Master::sendFrame delivers synchronously
    # and CombinerV2::acceptFrame only appends under its mutex.
    for _ in range(frameCount):
        prbsTx.genFrame(frameSize)
    assert combiner.getCount() == frameCount

    frameCountBefore = sink.getFrameCount()
    combiner.sendBatch()

    assert combiner.getCount() == 0
    assert sink.getFrameCount() - frameCountBefore == 1
