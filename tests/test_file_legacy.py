#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : File read and write test
#-----------------------------------------------------------------------------
# Description:
# File read and write test
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
import rogue.utilities.fileio
import pyrogue
import time
import rogue

#rogue.Logging.setLevel(rogue.Logging.Debug)

FrameCount = 10000
FrameSize  = 1000
BufferSize = 100000
MaxSize    = 1000000

def write_files():

    fwrU = rogue.utilities.fileio.LegacyStreamWriter()
    fwrU.setBufferSize(BufferSize)
    fwrU.setMaxSize(MaxSize)

    prbs = rogue.utilities.Prbs()

    prbs >> fwrU.getChannel(0)

    fwrU.open("legacy.dat")

    print("Writing data files")
    for _ in range(FrameCount):
        prbs.genFrame(FrameSize)

    time.sleep(5)
    fwrU.close()

def read_files():

    frdU = rogue.utilities.fileio.LegacyStreamReader()

    prbsU = rogue.utilities.Prbs()

    comp = rogue.utilities.StreamUnZip()

    frdU >> prbsU

    frdU.open("legacy.dat.1")

    print("Reading data files")
    frdU.closeWait()

    if prbsU.getRxCount() != FrameCount:
        raise AssertionError('Read uncompressed error. Incorrect number of frames read. Got = {} expected = {}'.format(prbsU.getRxCount(),FrameCount))

    if prbsU.getRxErrors() != 0:
        raise AssertionError('Read uncompressed error. PRBS Frame errors detected!')

def test_file_compress():
    return
    write_files()
    read_files()

if __name__ == "__main__":
    write_files()
    read_files()

