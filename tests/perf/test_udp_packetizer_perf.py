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

from tests.perf._perf_metrics import emit_perf_result
from tests.perf import _perf_harness

pytestmark = [pytest.mark.integration, pytest.mark.perf]


def _derive_bytes_on_wire_ratio(harness_metrics):
    """bytes_on_wire_ratio (Tier 1) is io_bytes over prbs_tx_bytes,
    derived here from the two Tier 1 counters _perf_harness.measure_benchmark
    already collected per repeat -- both share the same repeat set and guard
    outcome, so their per-repeat sample lists line up index for index --
    rather than a raw counter this harness could read and delta on its own.
    """
    io_entry = harness_metrics['io_bytes']
    tx_entry = harness_metrics['prbs_tx_bytes']
    ratios = [
        (io / tx) if tx else 0.0
        for io, tx in zip(io_entry['samples'], tx_entry['samples'])
    ]
    repeatability = _perf_harness.within_run_repeatability(ratios)
    entry = {
        'tier_candidate': _perf_harness.perf_tier_registry.TIER_1,
        'within_run_repeatability': repeatability,
        'rejected_samples': [],
        'n_clean': len(ratios),
        'samples': ratios,
        'status': io_entry['status'],
        'reason': io_entry['reason'],
    }
    if repeatability.get('verdict') == _perf_harness.VERDICT_UNSTABLE:
        entry['tier_demoted_to'] = _perf_harness.perf_tier_registry.TIER_2
        entry['demotion_reason'] = _perf_harness.DEMOTED_TO_TIER_2
        entry['min'] = repeatability['min']
        entry['max'] = repeatability['max']
        entry['spread'] = repeatability['spread']
    if entry['status'] == _perf_harness.STATUS_OK:
        entry['median'], entry['mad'] = _perf_harness.median_and_mad(ratios)
    return entry

#rogue.Logging.setLevel(rogue.Logging.Debug)

# Keep the original larger workload here so this file remains a meaningful
# soak / throughput benchmark for the UDP/RSSI/packetizer stack.
FrameCount = 10000
FrameSize  = 10000
DrainTimeout = 30.0

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
    def period(self,value):
        with self._lock:
            self._period = value

            # Send any cached frames if period is now 0
            if self._period == 0 and self._last is not None:
                self._sendFrame(self._last)
                self._last = None

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


def data_path(ver,jumbo):
    print("Testing ver={} jumbo={}".format(ver,jumbo))

    # UDP Server
    serv = rogue.protocols.udp.Server(0,jumbo)
    port = serv.getPort()

    # UDP Client
    client = rogue.protocols.udp.Client("127.0.0.1",port,jumbo)

    # RSSI
    sRssi = rogue.protocols.rssi.Server(serv.maxPayload() - 8)
    cRssi = rogue.protocols.rssi.Client(client.maxPayload() - 8)

    # Packetizer
    if ver == 1:
        sPack = rogue.protocols.packetizer.Core(True)
        cPack = rogue.protocols.packetizer.Core(True)
    else:
        sPack = rogue.protocols.packetizer.CoreV2(True,True,True)
        cPack = rogue.protocols.packetizer.CoreV2(True,True,True)

    # PRBS
    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()

    # Out of order module on client side
    coo = RssiOutOfOrder(period=0)

    # Client stream
    prbsTx >> cPack.application(0)
    cRssi.application() == cPack.transport()

    # Insert out of order in the outbound direction
    cRssi.transport() >> coo >> client >> cRssi.transport()

    # Server stream
    serv == sRssi.transport()
    sRssi.application() == sPack.transport()
    sPack.application(0) >> prbsRx

    # Start RSSI with out of order disabled
    sRssi._start()
    cRssi._start()

    # Wait for connection
    cnt = 0
    print("Waiting for RSSI connection")
    while not cRssi.getOpen():
        time.sleep(1)
        cnt += 1

        if cnt == 10:
            cRssi._stop()
            sRssi._stop()
            raise AssertionError('RSSI timeout error. Ver={} Jumbo={}'.format(ver,jumbo))

    # Enable out of order with a period of 10
    coo.period = 10

    print("Generating Frames")
    start = time.perf_counter()
    for _ in range(FrameCount):
        prbsTx.genFrame(FrameSize)

    # Disable out of order
    coo.period = 0

    # Wait for the stack to drain rather than assuming a fixed wall-clock delay.
    print("Waiting for frame drain")
    drain_start = time.time()
    while prbsRx.getRxCount() != FrameCount:
        time.sleep(0.1)
        if (time.time() - drain_start) > DrainTimeout:
            cRssi._stop()
            sRssi._stop()
            break

    # Stop connection
    print("Closing Link")
    cRssi._stop()
    sRssi._stop()

    elapsed = time.perf_counter() - start
    received = prbsRx.getRxCount()
    errors = prbsRx.getRxErrors()
    result = emit_perf_result(
        f"udp_packetizer_perf_v{ver}_{'jumbo' if jumbo else 'std'}",
        version=ver,
        jumbo=jumbo,
        frames_sent=FrameCount,
        frames_received=received,
        frame_size=FrameSize,
        elapsed_sec=elapsed,
        throughput_mb_s=((received * FrameSize) / (1024.0 * 1024.0)) / elapsed if elapsed > 0 else 0.0,
        rx_errors=errors,
        drain_complete=(received == FrameCount),
    )

    print(f"Perf metrics: {result}")

    assert received > 0, f"No frames were received. Ver={ver} Jumbo={jumbo}"
    assert errors == 0, f"PRBS frame errors detected. Ver={ver} Jumbo={jumbo}"

    # Tiered measurement harness (warmup repeats, measured repeats, a per-benchmark
    # wall-clock guard, and contamination rejection): this module's own
    # Tier 3 region already stopped the RSSI connection as part of its own
    # teardown (folded into the published elapsed_sec above), so the harness
    # reopens the same already-built serv/client/rssi/packetizer/prbs chain
    # rather than constructing a new one, runs its separate reduced-size
    # loop with its own counter snapshots, then closes it again.
    harness_reduced_count = max(1, FrameCount // 50)
    benchmark_name = f"udp_packetizer_perf_v{ver}_{'jumbo' if jumbo else 'std'}"

    sRssi._start()
    cRssi._start()
    reconnect_cnt = 0
    print("Waiting for RSSI reconnection for the harness")
    while not cRssi.getOpen():
        time.sleep(1)
        reconnect_cnt += 1
        if reconnect_cnt == 10:
            cRssi._stop()
            sRssi._stop()
            raise AssertionError(f'RSSI harness reconnect timeout. Ver={ver} Jumbo={jumbo}')

    def _harness_repeat():
        target = prbsRx.getRxCount() + harness_reduced_count
        for _ in range(harness_reduced_count):
            prbsTx.genFrame(FrameSize)
        drain_start = time.time()
        while prbsRx.getRxCount() < target:
            time.sleep(0.1)
            if (time.time() - drain_start) > DrainTimeout:
                break

    harness_stream_readers = {
        'buffer_copy_bytes': rogue.PerfCounters.getBufferCopyBytes,
        'buffer_copy_count': rogue.PerfCounters.getBufferCopyCount,
        'core_drop_count': sPack.getDropCount,
        'frame_create_count': rogue.PerfCounters.getFrameCreateCount,
        'frame_lock_acquisitions': rogue.PerfCounters.getFrameLockCount,
        'gil_acquire_count': rogue.PerfCounters.getGilAcquireCount,
        'gil_release_count': rogue.PerfCounters.getGilReleaseCount,
        'scoped_gil_count': rogue.PerfCounters.getScopedGilCount,
        'io_call_count': rogue.PerfCounters.getIoCallCount,
        'io_bytes': rogue.PerfCounters.getIoBytes,
        'prbs_rx_count': prbsRx.getRxCount,
        'prbs_rx_bytes': prbsRx.getRxBytes,
        'prbs_rx_errors': prbsRx.getRxErrors,
        'prbs_tx_count': prbsTx.getTxCount,
        'prbs_tx_bytes': prbsTx.getTxBytes,
        'prbs_tx_errors': prbsTx.getTxErrors,
    }
    harness_counter_readers = {
        metric_name: harness_stream_readers[metric_name]
        for metric_name in _perf_harness.perf_tier_registry.metrics_for_benchmark(benchmark_name)
        if metric_name in harness_stream_readers
    }
    harness_metrics = _perf_harness.measure_benchmark(
        benchmark_name,
        _harness_repeat,
        harness_counter_readers,
        bytes_per_repeat=harness_reduced_count * FrameSize,
        ops_per_repeat=harness_reduced_count,
    )
    harness_metrics['bytes_on_wire_ratio'] = _derive_bytes_on_wire_ratio(harness_metrics)
    harness_record = _perf_harness.build_harness_record(
        benchmark_name,
        harness_metrics,
        {"reduced_size": harness_reduced_count, "full_size": FrameCount},
    )
    _perf_harness.emit_harness_result(harness_record, benchmark_name)

    cRssi._stop()
    sRssi._stop()

    print("Done testing ver={} jumbo={}".format(ver,jumbo))

def test_data_path():
    data_path(1,True)
    data_path(2,True)
    data_path(1,False)
    data_path(2,False)

if __name__ == "__main__":
    test_data_path()
