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

#rogue.Logging.setLevel(rogue.Logging.Debug)

# Keep the default interfaces test focused on FIFO correctness rather than
# throughput. The larger soak workload now lives in tests/perf/test_fifo_perf.py.
FRAME_COUNT = 200
FRAME_SIZE = 2048
FRAME_DRAIN_POLLS = 200
FRAME_DRAIN_INTERVAL = 0.1

def fifo_path():

    # PRBS
    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()

    # FIFO
    fifo = rogue.interfaces.stream.Fifo(0,0,False)

    # Client stream
    prbsTx >> fifo >> prbsRx

    prbsRx.checkPayload(True)

    print("Generating Frames")
    for _ in range(FRAME_COUNT):
        prbsTx.genFrame(FRAME_SIZE)

    # Allow time for the FIFO path to drain without turning this into a soak.
    for _ in range(FRAME_DRAIN_POLLS):
        if prbsRx.getRxCount() == FRAME_COUNT:
            break
        time.sleep(FRAME_DRAIN_INTERVAL)

    if prbsRx.getRxErrors() != 0:
        raise AssertionError('PRBS Frame errors detected! Errors = {}'.format(prbsRx.getRxErrors()))

    if prbsRx.getRxCount() != FRAME_COUNT:
        raise AssertionError('Frame count error. Got = {} expected = {}'.format(prbsRx.getRxCount(),FRAME_COUNT))

    print("Done testing")

def test_fifo_path():
    fifo_path()

if __name__ == "__main__":
    test_fifo_path()
