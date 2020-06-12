#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

# Comment added by rherbst for demonstration purposes.
import datetime
import parse
import pyrogue as pr
import pyrogue.interfaces.simulation
import rogue.interfaces.memory
import time

#rogue.Logging.setLevel(rogue.Logging.Debug)
#import logging
#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

class AxiVersion(pr.Device):

    # Last comment added by rherbst for demonstration.
    def __init__(
            self,
            name             = 'AxiVersion',
            description      = 'AXI-Lite Version Module',
            numUserConstants = 0,
            **kwargs):

        super().__init__(
            name        = name,
            description = description,
            **kwargs)

        ##############################
        # Variables
        ##############################

        self.add(pr.RemoteVariable(
            name         = 'ScratchPad',
            description  = 'Register to test reads and writes',
            offset       = 0x04,
            bitSize      = 32,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{:#08x}'
        ))

        self.add(pr.RemoteVariable(
            name         = 'UpTimeCnt',
            description  = 'Number of seconds since last reset',
            hidden       = True,
            offset       = 0x08,
            bitSize      = 32,
            bitOffset    = 0x00,
            base         = pr.UInt,
            mode         = 'RO',
            disp         = '{:d}',
            units        = 'seconds',
            pollInterval = 1
        ))

        for i in range(4):
            # 4 bytes all in the same 32-bit address alignment
            self.add(pr.RemoteVariable(
                name         = f'TestBlockBytes[{i}]',
                offset       = 0x10,
                bitSize      = 8,
                bitOffset    = 8*i,
                mode         = 'RO',
                value        = i,
            ))

        for i in range(128):
            # Sweeping across a non-byte remote variable with overlapping 32-bit address alignments
            # with same offsets for all variables (sometimes ASIC designers do this registers definition)
            self.add(pr.RemoteVariable(
                name         = f'TestBlockBits[{i}]',
                offset       = 0x100,
                bitSize      = 7,
                bitOffset    = 7*i,
                mode         = 'RO',
                value        = i,
            ))


class DummyTree(pr.Root):

    def __init__(self):
        pr.Root.__init__(self,
                         name='dummyTree',
                         description="Dummy tree for example",
                         timeout=2.0,
                         pollEn=False,
                         serverPort=None)

        # Use a memory space emulator
        self.sim = pr.interfaces.simulation.MemEmulate()

        # Create a memory gateway
        self.ms = rogue.interfaces.memory.TcpServer("127.0.0.1",9080);

        # Connect the memory gateways together
        self.sim << self.ms

        # Create a memory gateway
        self.mc = rogue.interfaces.memory.TcpClient("127.0.0.1",9080);

        # Add Device
        self.add(AxiVersion(memBase=self.mc,offset=0x0))

    def stop(self):
        self.ms.close()
        self.mc.close()
        pr.Root.stop(self)

def test_memory():

    with DummyTree() as root:
        time.sleep(5)

        print("Writing 0x50 to scratchpad")
        root.AxiVersion.ScratchPad.set(0x50)

        ret = root.AxiVersion.ScratchPad.get()
        print("Read {:#x} from scratchpad".format(ret))

        time.sleep(5)

        if ret != 0x50:
            raise AssertionError('Scratchpad Mismatch')

        for i in range(4):
            ret = root.AxiVersion.TestBlockBytes[i].get()
            if ret != i:
                raise AssertionError(f'TestBlockBytes[i] Mismatch: Should be {i} but got {ret}')

        for i in range(128):
            ret = root.AxiVersion.TestBlockBits[i].get()
            if ret != i:
                raise AssertionError(f'TestBlockBits[i] Mismatch: Should be {i} but got {ret}')

if __name__ == "__main__":
    test_memory()

