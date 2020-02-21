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
BufferSize = 100004
MaxSize    = 1000003

def write_files():

    fwrC = rogue.utilities.fileio.StreamWriter()
    fwrC.setBufferSize(BufferSize)
    fwrC.setMaxSize(MaxSize)

    fwrU = rogue.utilities.fileio.StreamWriter()
    fwrU.setBufferSize(BufferSize)
    fwrU.setMaxSize(MaxSize)

    prbs = rogue.utilities.Prbs()

    comp = rogue.utilities.StreamZip()

    prbs >> fwrU.getChannel(0)
    prbs >> comp >> fwrC.getChannel(0)

    fwrC.open("compressed.dat")
    fwrU.open("uncompressed.dat")

    print("Writing data files")
    for _ in range(FrameCount):
        prbs.genFrame(FrameSize)

    time.sleep(5)
    fwrC.close()
    fwrU.close()

def read_files():

    frdC = rogue.utilities.fileio.StreamReader()
    frdU = rogue.utilities.fileio.StreamReader()

    prbsC = rogue.utilities.Prbs()
    prbsU = rogue.utilities.Prbs()

    comp = rogue.utilities.StreamUnZip()

    frdU >> prbsU
    frdC >> comp >> prbsC

    frdU.open("uncompressed.dat.1")
    frdC.open("compressed.dat.1")

    print("Reading data files")
    frdU.closeWait()
    frdC.closeWait()

    if prbsU.getRxCount() != FrameCount:
        raise AssertionError('Read uncompressed error. Incorrect number of frames read. Got = {} expected = {}'.format(prbsU.getRxCount(),FrameCount))

    if prbsU.getRxErrors() != 0:
        raise AssertionError('Read uncompressed error. PRBS Frame errors detected!')

    if prbsC.getRxCount() != FrameCount:
        raise AssertionError('Read compressed error. Incorrect number of frames read. Got = {} expected = {}'.format(prbsC.getRxCount(),FrameCount))

    if prbsC.getRxErrors() != 0:
        raise AssertionError('Read compressed error. PRBS Frame errors detected!')

def test_file_compress():
    return
    write_files()
    read_files()

if __name__ == "__main__":
    write_files()
    read_files()


