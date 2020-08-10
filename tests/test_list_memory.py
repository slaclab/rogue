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

#rogue.Logging.setLevel(rogue.Logging.Warning)
#import logging
#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

class ListDevice(pr.Device):

    # Last comment added by rherbst for demonstration.
    def __init__(
            self,
            name             = 'ListDevice',
            description      = 'List Device Test',
            **kwargs):

        super().__init__(
            name        = name,
            description = description,
            **kwargs)

        ##############################
        # Variables
        ##############################

        self.add(pr.RemoteVariable(
            name         = 'UInt32List',
            offset       = 0x0000,
            bitSize      = 32 * 32,
            bitOffset    = 0x0000,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 32,
            valueStride  = 32
        ))

        self.add(pr.RemoteVariable(
            name         = 'FloatList',
            offset       = 0x0100,
            bitSize      = 32 * 32,
            bitOffset    = 0x0000,
            base         = pr.Float,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 32,
            valueStride  = 32
        ))

        self.add(pr.RemoteVariable(
            name         = 'UInt16List',
            offset       = 0x0200,
            bitSize      = 16 * 32,
            bitOffset    = 0x0000,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 16,
            valueStride  = 16
        ))

        self.add(pr.RemoteVariable(
            name         = 'UInt21List',
            offset       = 0x0300,
            bitSize      = 32 * 32,
            bitOffset    = 0x0000,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 21,
            valueStride  = 32
        ))

        self.add(pr.RemoteVariable(
            name         = 'BoolList',
            offset       = 0x0400,
            bitSize      = 32,
            bitOffset    = 0x0000,
            base         = pr.Bool,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 1,
            valueStride  = 1
        ))

        self.add(pr.RemoteVariable(
            name         = 'StringList',
            offset       = 0x0500,
            bitSize      = 8*16*32,
            bitOffset    = 0x0000,
            base         = pr.String,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 8*16,
            valueStride  = 8*16
        ))

class DummyTree(pr.Root):

    def __init__(self):
        pr.Root.__init__(self,
                         name='dummyTree',
                         description="Dummy tree for example",
                         timeout=2.0,
                         pollEn=False)
                         #serverPort=None)

        # Use a memory space emulator
        sim = pr.interfaces.simulation.MemEmulate()
        self.addInterface(sim)

        self.add(ListDevice(
            offset     = 0,
            memBase    = sim
        ))

#def test_memory():
#
#    with DummyTree() as root:
#
#        # Load the R/W variables
#        for dev in range(2):
#            writeVar = (dev == 0)
#            for i in range(256):
#                root.MemDev[dev].TestBlockBytes[i].set(value=i,write=writeVar)
#                root.MemDev[dev].TestBlockBits[i].set(value=i,write=writeVar)
#
#        # Bulk Write Device
#        root.MemDev[1].WriteDevice()
#
#        # Bulk Read Device
#        root.MemDev[3].ReadDevice()
#
#        # Verify all the RW and RO variables
#        for dev in range(4):
#            for i in range(256):
#                if dev!=3:
#                    retByte = root.MemDev[dev].TestBlockBytes[i].get()
#                    retBit  = root.MemDev[dev].TestBlockBits[i].get()
#                else:
#                    retByte = root.MemDev[dev].TestBlockBytes[i].value()
#                    retBit  = root.MemDev[dev].TestBlockBits[i].value()
#                if (retByte != i) or (retBit != i):
#                    raise AssertionError(f'{root.MemDev[dev].path}: Verification Failure: i={i}, TestBlockBytes={retByte}, TestBlockBits={retBit}')

if __name__ == "__main__":
    #test_memory()

    import pyrogue.pydm

    with DummyTree() as root:
        root.ListDevice.UInt32List.set([i for i in range(32)])
        root.ListDevice.FloatList.set([i/2 for i in range(32)])
        root.ListDevice.UInt16List.set([i for i in range(32)])
        root.ListDevice.UInt21List.set([i for i in range(32)])
        root.ListDevice.BoolList.set([i%2==0 for i in range(32)])
        root.ListDevice.StringList.set([str(i) for i in range(32)])

        print(str(root.ListDevice.UInt32List.get()))
        print(str(root.ListDevice.FloatList.get()))
        print(str(root.ListDevice.UInt16List.get()))
        print(str(root.ListDevice.UInt21List.get()))
        print(str(root.ListDevice.BoolList.get()))
        print(str(root.ListDevice.StringList.get()))
        print(str(root.ListDevice.StringList.get(index=2)))

        pyrogue.pydm.runPyDM(root=root,title='test123',sizeX=1000,sizeY=500)
