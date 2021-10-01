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
import pyrogue as pr
import pyrogue.interfaces.simulation
import numpy as np

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

def test_memory():

    UInt32ListA = np.array([i for i in range(32)],np.uint64)
    FloatListA  = np.array([i/2 for i in range(32)],np.float32)
    UInt16ListA = np.array([i for i in range(32)],np.uint64)
    UInt21ListA = np.array([i for i in range(32)],np.uint64)
    BoolListA   = np.array([i%2==0 for i in range(32)],np.bool)

    UInt32ListB = np.array([i+1 for i in range(32)],np.uint64)
    FloatListB  = np.array([(i+1)/2 for i in range(32)],np.float32)
    UInt16ListB = np.array([i+1 for i in range(32)],np.uint64)
    UInt21ListB = np.array([i+1 for i in range(32)],np.uint64)
    BoolListB   = np.array([(i+1)%2==0 for i in range(32)],np.bool)

    with DummyTree() as root:

        root.ListDevice.UInt32List.set(UInt32ListA)
        root.ListDevice.FloatList.set(FloatListA)
        root.ListDevice.UInt16List.set(UInt16ListA)
        root.ListDevice.UInt21List.set(UInt21ListA)
        root.ListDevice.BoolList.set(BoolListA)

        UInt32ListAA = root.ListDevice.UInt32List.get()
        FloatListAA  = root.ListDevice.FloatList.get()
        UInt16ListAA = root.ListDevice.UInt16List.get()
        UInt21ListAA = root.ListDevice.UInt21List.get()
        BoolListAA   = root.ListDevice.BoolList.get()

        UInt32ListAB = np.array([0] * 32,np.int64)
        FloatListAB  = np.array([0] * 32,np.float32)
        UInt16ListAB = np.array([0] * 32,np.int64)
        UInt21ListAB = np.array([0] * 32,np.int64)
        BoolListAB   = np.array([0] * 32,np.bool)

        for i in range(32):
            UInt32ListAB[i] = root.ListDevice.UInt32List.get(index=i)
            FloatListAB[i]  = root.ListDevice.FloatList.get(index=i)
            UInt16ListAB[i] = root.ListDevice.UInt16List.get(index=i)
            UInt21ListAB[i] = root.ListDevice.UInt21List.get(index=i)
            BoolListAB[i]   = root.ListDevice.BoolList.get(index=i)

        for i in range(32):
            if UInt32ListAA[i] != UInt32ListA[i]:
                raise AssertionError(f'Verification Failure for UInt32ListAA at position {i}')

            if FloatListAA[i] != FloatListA[i]:
                raise AssertionError(f'Verification Failure for FloatListAA at position {i}')

            if UInt16ListAA[i] != UInt16ListA[i]:
                raise AssertionError(f'Verification Failure for UInt16ListAA at position {i}')

            if UInt21ListAA[i] != UInt21ListA[i]:
                raise AssertionError(f'Verification Failure for UInt21ListAA at position {i}')

            if BoolListAA[i] != BoolListA[i]:
                raise AssertionError(f'Verification Failure for BoolListAA at position {i}')

            if UInt32ListAB[i] != UInt32ListA[i]:
                raise AssertionError(f'Verification Failure for UInt32ListAB at position {i}')

            if FloatListAB[i] != FloatListA[i]:
                raise AssertionError(f'Verification Failure for FloatListAB at position {i}')

            if UInt16ListAB[i] != UInt16ListA[i]:
                raise AssertionError(f'Verification Failure for UInt16ListAB at position {i}')

            if UInt21ListAB[i] != UInt21ListA[i]:
                raise AssertionError(f'Verification Failure for UInt21ListAB at position {i}')

            if BoolListAB[i] != BoolListA[i]:
                raise AssertionError(f'Verification Failure for BoolListAB at position {i}')

        for i in range(32):
            root.ListDevice.UInt32List.set(UInt32ListB[i],index=i)
            root.ListDevice.FloatList.set(FloatListB[i],index=i)
            root.ListDevice.UInt16List.set(UInt16ListB[i],index=i)
            root.ListDevice.UInt21List.set(UInt21ListB[i],index=i)
            root.ListDevice.BoolList.set(BoolListB[i],index=i)

        UInt32ListBA = root.ListDevice.UInt32List.get()
        FloatListBA  = root.ListDevice.FloatList.get()
        UInt16ListBA = root.ListDevice.UInt16List.get()
        UInt21ListBA = root.ListDevice.UInt21List.get()
        BoolListBA   = root.ListDevice.BoolList.get()

        UInt32ListBB = np.array([0] * 32,np.int64)
        FloatListBB  = np.array([0] * 32,np.float32)
        UInt16ListBB = np.array([0] * 32,np.int64)
        UInt21ListBB = np.array([0] * 32,np.int64)
        BoolListBB   = np.array([0] * 32,np.bool)

        for i in range(32):
            UInt32ListBB[i] = root.ListDevice.UInt32List.get(index=i)
            FloatListBB[i]  = root.ListDevice.FloatList.get(index=i)
            UInt16ListBB[i] = root.ListDevice.UInt16List.get(index=i)
            UInt21ListBB[i] = root.ListDevice.UInt21List.get(index=i)
            BoolListBB[i]   = root.ListDevice.BoolList.get(index=i)

        for i in range(32):
            if UInt32ListBA[i] != UInt32ListB[i]:
                raise AssertionError(f'Verification Failure for UInt32ListBA at position {i}')

            if FloatListBA[i] != FloatListB[i]:
                raise AssertionError(f'Verification Failure for FloatListBA at position {i}')

            if UInt16ListBA[i] != UInt16ListB[i]:
                raise AssertionError(f'Verification Failure for UInt16ListBA at position {i}')

            if UInt21ListBA[i] != UInt21ListB[i]:
                raise AssertionError(f'Verification Failure for UInt21ListBA at position {i}')

            if BoolListBA[i] != BoolListB[i]:
                raise AssertionError(f'Verification Failure for BoolListBA at position {i}')

            if UInt32ListBB[i] != UInt32ListB[i]:
                raise AssertionError(f'Verification Failure for UInt32ListBB at position {i}')

            if FloatListBB[i] != FloatListB[i]:
                raise AssertionError(f'Verification Failure for FloatListBB at position {i}')

            if UInt16ListBB[i] != UInt16ListB[i]:
                raise AssertionError(f'Verification Failure for UInt16ListBB at position {i}')

            if UInt21ListBB[i] != UInt21ListB[i]:
                raise AssertionError(f'Verification Failure for UInt21ListBB at position {i}')

            if BoolListBB[i] != BoolListB[i]:
                raise AssertionError(f'Verification Failure for BoolListBB at position {i}')

def run_gui():
    import pyrogue.pydm

    with DummyTree() as root:
        pyrogue.pydm.runPyDM(root=root,title='test123',sizeX=1000,sizeY=500)

if __name__ == "__main__":
    test_memory()
    #run_gui()

