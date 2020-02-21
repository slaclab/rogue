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
import pyrogue
import time

#rogue.Logging.setLevel(rogue.Logging.Debug)

FrameCount = 10000
FrameSize  = 10000

def fifo_path():

    # PRBS
    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()

    # FIFO
    fifo = rogue.interfaces.stream.Fifo(0,0,False);

    # Client stream
    prbsTx >> fifo >> prbsRx

    print("Generating Frames")
    for _ in range(FrameCount):
        prbsTx.genFrame(FrameSize)
    time.sleep(30)

    if prbsRx.getRxErrors() != 0:
        raise AssertionError('PRBS Frame errors detected! Errors = {}'.format(prbsRx.getRxErrors()))

    if prbsRx.getRxCount() != FrameCount:
        raise AssertionError('Frame count error. Got = {} expected = {}'.format(prbsRx.getRxCount(),FrameCount))

    print("Done testing")

def test_fifo_path():
    fifo_path()

if __name__ == "__main__":
    test_fifo_path()

