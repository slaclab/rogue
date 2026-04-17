#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : FIFO stream performance test
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.stream
import rogue
import time
import pytest

from tests.perf._perf_metrics import emit_perf_result

pytestmark = [pytest.mark.integration, pytest.mark.perf]

#rogue.Logging.setLevel(rogue.Logging.Debug)

# Preserve the original larger FIFO workload as the recorded soak benchmark.
FRAME_COUNT = 10000
FRAME_SIZE = 10000
FRAME_DRAIN_POLLS = 300
FRAME_DRAIN_INTERVAL = 0.1


def fifo_path():

    # PRBS
    prbs_tx = rogue.utilities.Prbs()
    prbs_rx = rogue.utilities.Prbs()

    # FIFO
    fifo = rogue.interfaces.stream.Fifo(0, 0, False)

    # Client stream
    prbs_tx >> fifo >> prbs_rx

    prbs_rx.checkPayload(True)

    print("Generating Frames")
    start = time.perf_counter()
    for _ in range(FRAME_COUNT):
        prbs_tx.genFrame(FRAME_SIZE)

    for _ in range(FRAME_DRAIN_POLLS):
        if prbs_rx.getRxCount() == FRAME_COUNT:
            break
        time.sleep(FRAME_DRAIN_INTERVAL)

    elapsed = time.perf_counter() - start
    received = prbs_rx.getRxCount()
    errors = prbs_rx.getRxErrors()
    result = emit_perf_result(
        "fifo_perf",
        frames_sent=FRAME_COUNT,
        frames_received=received,
        frame_size=FRAME_SIZE,
        elapsed_sec=elapsed,
        throughput_mb_s=((received * FRAME_SIZE) / (1024.0 * 1024.0)) / elapsed if elapsed > 0 else 0.0,
        rx_errors=errors,
        drain_complete=(received == FRAME_COUNT),
    )

    print(f"Perf metrics: {result}")

    assert received > 0, "No frames were received during the FIFO perf run"
    assert errors == 0, f"PRBS frame errors detected: {errors}"
    assert received == FRAME_COUNT, f"Frame count error. Got = {received} expected = {FRAME_COUNT}"

    print("Done testing")


def test_fifo_path():
    fifo_path()


if __name__ == "__main__":
    test_fifo_path()
