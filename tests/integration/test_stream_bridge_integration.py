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

pytestmark = pytest.mark.integration

# This test is an end-to-end bridge regression check, not a throughput
# benchmark. Keep the payload modest so it still exercises the real TCP stream
# path without dominating integration runtime.
FRAME_COUNT = 200
FRAME_SIZE = 2048
FRAME_DRAIN_POLLS = 200
FRAME_DRAIN_INTERVAL = 0.1


def run_stream_bridge_path(port):
    """Validate TCP bridge delivery with PRBS payload checking enabled."""
    server = rogue.interfaces.stream.TcpServer("127.0.0.1", port)
    client = rogue.interfaces.stream.TcpClient("127.0.0.1", port)

    prbs_tx = rogue.utilities.Prbs()
    prbs_rx = rogue.utilities.Prbs()

    server << prbs_tx
    prbs_rx << client

    prbs_rx.checkPayload(True)

    for _ in range(FRAME_COUNT):
        prbs_tx.genFrame(FRAME_SIZE)

    # Allow time for the stream path to drain, but do not turn the test into a
    # long-running soak benchmark.
    for _ in range(FRAME_DRAIN_POLLS):
        if prbs_rx.getRxCount() == FRAME_COUNT:
            break
        time.sleep(FRAME_DRAIN_INTERVAL)

    assert prbs_rx.getRxCount() == FRAME_COUNT
    assert prbs_rx.getRxErrors() == 0

def test_data_path(free_tcp_port):
    run_stream_bridge_path(free_tcp_port)

if __name__ == "__main__":
    run_stream_bridge_path(9000)
