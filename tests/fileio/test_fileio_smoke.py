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
import os
import tempfile

import rogue.utilities
import rogue.utilities.fileio
import pyrogue.utilities.fileio
import pyrogue
import time
import rogue

#rogue.Logging.setLevel(rogue.Logging.Debug)

FrameCount = 10000
FrameSize  = 1000
BufferSize = 100004
MaxSize    = 1000003

def write_files(dirName):

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

    # StreamWriter refuses to open an existing file, so always write into a
    # fresh directory rather than the working directory.
    fwrC.open(os.path.join(dirName, "compressed.dat"))
    fwrU.open(os.path.join(dirName, "uncompressed.dat"))

    print("Writing data files")
    for _ in range(FrameCount):
        prbs.genFrame(FrameSize)

    time.sleep(5)
    fwrC.close()
    fwrU.close()

def read_files(dirName):

    frdC = rogue.utilities.fileio.StreamReader()
    frdU = rogue.utilities.fileio.StreamReader()

    prbsC = rogue.utilities.Prbs()
    prbsU = rogue.utilities.Prbs()

    comp = rogue.utilities.StreamUnZip()

    frdU >> prbsU
    frdC >> comp >> prbsC

    frdU.open(os.path.join(dirName, "uncompressed.dat.1"))
    frdC.open(os.path.join(dirName, "compressed.dat.1"))

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

def file_reader(dirName):
    print("pyrogue file reader")
    with pyrogue.utilities.fileio.FileReader(files=os.path.join(dirName, "uncompressed.dat.1")) as fd:
        for header,data in fd.records():
            if header.size != FrameSize:
                raise AssertionError('frame size mismatch detected in FileReader')
            if header.error != 0:
                raise AssertionError('Error Flag detected in FileReader')

def test_file_compress(tmp_path):
    return
    write_files(str(tmp_path))
    read_files(str(tmp_path))
    file_reader(str(tmp_path))

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as dirName:
        write_files(dirName)
        read_files(dirName)
        file_reader(dirName)
