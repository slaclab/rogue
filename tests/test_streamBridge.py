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

def data_path():

    # Bridge server
    serv = rogue.interfaces.stream.TcpServer("127.0.0.1",9000)

    # Bridge client
    client = rogue.interfaces.stream.TcpClient("127.0.0.1",9000)

    # PRBS
    prbsTx = rogue.utilities.Prbs()
    prbsRx = rogue.utilities.Prbs()

    # Client stream
    serv << prbsTx

    # Server stream
    prbsRx << client

    time.sleep(5)

    print("Generating Frames")
    for _ in range(FrameCount):
        prbsTx.genFrame(FrameSize)
    time.sleep(20)

    if prbsRx.getRxCount() != FrameCount:
        raise AssertionError('Frame count error. Got = {} expected = {}'.format(prbsRx.getRxCount(),FrameCount))

    if prbsRx.getRxErrors() != 0:
        raise AssertionError('PRBS Frame errors detected! Errors = {}'.format(prbsRx.getRxErrors()))

    print("Done testing")

def test_data_path():
    data_path()

if __name__ == "__main__":
    test_data_path()

