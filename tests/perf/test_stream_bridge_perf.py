#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Data over stream bridge test script
#-----------------------------------------------------------------------------
# This file is part of the rogue_example software. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue_example software, including this file, may be
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

# Keep the original larger payload here so this file serves as a soak /
# throughput-style benchmark rather than a correctness-focused regression test.
FrameCount = 10000
FrameSize  = 10000
def data_path(port):
    # Bridge server
    serv = rogue.interfaces.stream.TcpServer("127.0.0.1", port)

    # Bridge client
    client = rogue.interfaces.stream.TcpClient("127.0.0.1", port)

    # PRBS
    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()

    # Client stream
    serv << prbsTx

    # Server stream
    prbsRx << client

    prbsRx.checkPayload(True)

    print("Generating Frames")
    start = time.perf_counter()
    for _ in range(FrameCount):
        prbsTx.genFrame(FrameSize)

    # Wait long enough for the higher-volume perf workload to drain.
    for i in range(200):
        if prbsRx.getRxCount() == FrameCount:
            break
        time.sleep(.1)

    elapsed = time.perf_counter() - start
    received = prbsRx.getRxCount()
    errors = prbsRx.getRxErrors()
    result = emit_perf_result(
        "stream_bridge_perf",
        frames_sent=FrameCount,
        frames_received=received,
        frame_size=FrameSize,
        elapsed_sec=elapsed,
        throughput_mb_s=((received * FrameSize) / (1024.0 * 1024.0)) / elapsed if elapsed > 0 else 0.0,
        rx_errors=errors,
        drain_complete=(received == FrameCount),
    )

    print(f"Perf metrics: {result}")

    assert received > 0, "No frames were received during the stream bridge perf run"
    assert errors == 0, f"PRBS frame errors detected: {errors}"

    print("Done testing")

def test_data_path(free_tcp_port):
    data_path(free_tcp_port)

if __name__ == "__main__":
    data_path(9000)
