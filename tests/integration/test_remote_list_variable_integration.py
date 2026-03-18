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

import pyrogue as pr
import rogue.interfaces.memory
import numpy as np
import random
import pytest

pytestmark = pytest.mark.integration

class RemoteListDevice(pr.Device):
    def __init__(
            self,
            name             = 'RemoteListDevice',
            description      = 'List Device Test',
            **kwargs):

        super().__init__(
            name        = name,
            description = description,
            **kwargs)

        self.add(pr.RemoteVariable(
            name         = 'UInt32List',
            offset       = 0x0000,
            bitOffset    = 0x0000,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 32,
            valueStride  = 32
        ))

        self.add(pr.RemoteVariable(
            name         = 'Int32List',
            offset       = 0x1000,
            bitOffset    = 0x0000,
            base         = pr.Int,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 32,
            valueStride  = 32
        ))

        self.add(pr.RemoteVariable(
            name         = 'UInt48List',
            offset       = 0x2000,
            bitOffset    = 0x0000,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 48,
            valueStride  = 48
        ))

        self.add(pr.RemoteVariable(
            name         = 'FloatList',
            offset       = 0x3000,
            bitOffset    = 0x0000,
            base         = pr.Float,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 32,
            valueStride  = 32
        ))

        self.add(pr.RemoteVariable(
            name         = 'DoubleList',
            offset       = 0x4000,
            bitOffset    = 0x0000,
            base         = pr.Double,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 64,
            valueStride  = 64
        ))

        self.add(pr.RemoteVariable(
            name         = 'UInt16List',
            offset       = 0x5000,
            bitOffset    = 0x0000,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 16,
            valueStride  = 16
        ))

        self.add(pr.RemoteVariable(
            name         = 'UInt16Pack0',
            offset       = 0x6000,
            bitOffset    = 0x0000,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 16,
            valueStride  = 32
        ))

        self.add(pr.RemoteVariable(
            name         = 'UInt16Pack1',
            offset       = 0x6000,
            bitOffset    = 16,
            base         = pr.UInt,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 16,
            valueStride  = 32
        ))

        self.add(pr.RemoteVariable(
            name         = 'UInt21List',
            offset       = 0x7000,
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
            offset       = 0x8000,
            bitOffset    = 0x0000,
            base         = pr.Bool,
            mode         = 'RW',
            disp         = '{}',
            numValues    = 32,
            valueBits    = 1,
            valueStride  = 1
        ))

class RemoteListRoot(pr.Root):
    def __init__(self):
        super().__init__(name='dummyTree', description="Dummy tree for example", timeout=2.0, pollEn=False)

        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        self.addInterface(sim)

        self.add(RemoteListDevice(
            offset     = 0,
            memBase    = sim
        ))

def assert_array_matches(actual, expected, name, atol=0.001):
    if np.issubdtype(expected.dtype, np.floating):
        assert np.allclose(actual, expected, atol=atol), f"{name} mismatch"
    else:
        assert np.array_equal(actual, expected), f"{name} mismatch"


def test_memory():

    UInt32ListARaw  = [int(random.random()*1000) for i in range(32)]
    Int32ListARaw   = [int(random.random()*1000) for i in range(32)]
    UInt48ListARaw  = [int(random.random()*1000) for i in range(32)]
    FloatListARaw   = [random.random()*1000 for i in range(32)]
    DoubleListARaw  = [random.random()*1000 for i in range(32)]
    UInt16ListARaw  = [int(random.random()*1000) for i in range(32)]
    UInt16Pack0ARaw = [int(random.random()*1000) for i in range(32)]
    UInt16Pack1ARaw = [int(random.random()*1000) for i in range(32)]
    UInt21ListARaw  = [int(random.random()*1000) for i in range(32)]
    BoolListARaw    = [int(random.random()*1000)%2==0 for i in range(32)]

    UInt32ListA  = np.array(UInt32ListARaw,np.uint32)
    Int32ListA   = np.array(Int32ListARaw,np.int32)
    UInt48ListA  = np.array(UInt48ListARaw,np.uint64)
    FloatListA   = np.array(FloatListARaw,np.float32)
    DoubleListA  = np.array(DoubleListARaw,np.float64)
    UInt16ListA  = np.array(UInt16ListARaw,np.uint16)
    UInt16Pack0A = np.array(UInt16Pack0ARaw,np.uint16)
    UInt16Pack1A = np.array(UInt16Pack1ARaw,np.uint16)
    UInt21ListA  = np.array(UInt21ListARaw,np.uint32)
    BoolListA    = np.array(BoolListARaw,bool)

    UInt32ListB  = [int(random.random()*1000) for i in range(32)]
    Int32ListB   = [int(random.random()*1000) for i in range(32)]
    UInt48ListB  = [int(random.random()*1000) for i in range(32)]
    FloatListB   = [random.random()*1000 for i in range(32)]
    DoubleListB  = [random.random()*1000 for i in range(32)]
    UInt16ListB  = [int(random.random()*1000) for i in range(32)]
    UInt16Pack0B = [int(random.random()*1000) for i in range(32)]
    UInt16Pack1B = [int(random.random()*1000) for i in range(32)]
    UInt21ListB  = [int(random.random()*1000) for i in range(32)]
    BoolListB    = [int(random.random()*1000)%2==0 for i in range(32)]

    with RemoteListRoot() as root:

        with root.updateGroup():
            root.RemoteListDevice.UInt32List.set(UInt32ListARaw)
            root.RemoteListDevice.Int32List.set(Int32ListARaw)
            root.RemoteListDevice.UInt48List.set(UInt48ListARaw)
            root.RemoteListDevice.FloatList.set(FloatListARaw)
            root.RemoteListDevice.DoubleList.set(DoubleListARaw)
            root.RemoteListDevice.UInt16List.set(UInt16ListARaw)
            root.RemoteListDevice.UInt16Pack0.set(UInt16Pack0ARaw)
            root.RemoteListDevice.UInt16Pack1.set(UInt16Pack1ARaw)
            root.RemoteListDevice.UInt21List.set(UInt21ListARaw)
            root.RemoteListDevice.BoolList.set(BoolListARaw)

            UInt32ListAA  = root.RemoteListDevice.UInt32List.get()
            Int32ListAA   = root.RemoteListDevice.Int32List.get()
            UInt48ListAA  = root.RemoteListDevice.UInt48List.get()
            FloatListAA   = root.RemoteListDevice.FloatList.get()
            DoubleListAA  = root.RemoteListDevice.DoubleList.get()
            UInt16ListAA  = root.RemoteListDevice.UInt16List.get()
            UInt16Pack0AA = root.RemoteListDevice.UInt16Pack0.get()
            UInt16Pack1AA = root.RemoteListDevice.UInt16Pack1.get()
            UInt21ListAA  = root.RemoteListDevice.UInt21List.get()
            BoolListAA    = root.RemoteListDevice.BoolList.get()

            UInt32ListAB  = np.array([0] * 32,np.uint32)
            Int32ListAB   = np.array([0] * 32,np.int32)
            UInt48ListAB  = np.array([0] * 32,np.uint64)
            FloatListAB   = np.array([0] * 32,np.float32)
            DoubleListAB  = np.array([0] * 32,np.float64)
            UInt16ListAB  = np.array([0] * 32,np.uint16)
            UInt16Pack0AB = np.array([0] * 32,np.uint16)
            UInt16Pack1AB = np.array([0] * 32,np.uint16)
            UInt21ListAB  = np.array([0] * 32,np.uint32)
            BoolListAB    = np.array([0] * 32,bool)

            for i in range(32):
                UInt32ListAB[i]  = root.RemoteListDevice.UInt32List.get(index=i)
                Int32ListAB[i]   = root.RemoteListDevice.Int32List.get(index=i)
                UInt48ListAB[i]  = root.RemoteListDevice.UInt48List.get(index=i)
                FloatListAB[i]   = root.RemoteListDevice.FloatList.get(index=i)
                DoubleListAB[i]  = root.RemoteListDevice.DoubleList.get(index=i)
                UInt16ListAB[i]  = root.RemoteListDevice.UInt16List.get(index=i)
                UInt16Pack0AB[i] = root.RemoteListDevice.UInt16Pack0.get(index=i)
                UInt16Pack1AB[i] = root.RemoteListDevice.UInt16Pack1.get(index=i)
                UInt21ListAB[i]  = root.RemoteListDevice.UInt21List.get(index=i)
                BoolListAB[i]    = root.RemoteListDevice.BoolList.get(index=i)

            assert_array_matches(UInt32ListAA, UInt32ListA, "UInt32ListAA")
            assert_array_matches(Int32ListAA, Int32ListA, "Int32ListAA")
            assert_array_matches(UInt48ListAA, UInt48ListA, "UInt48ListAA")
            assert_array_matches(FloatListAA, FloatListA, "FloatListAA")
            assert_array_matches(DoubleListAA, DoubleListA, "DoubleListAA")
            assert_array_matches(UInt16ListAA, UInt16ListA, "UInt16ListAA")
            assert_array_matches(UInt16Pack0AA, UInt16Pack0A, "UInt16Pack0AA")
            assert_array_matches(UInt16Pack1AA, UInt16Pack1A, "UInt16Pack1AA")
            assert_array_matches(UInt21ListAA, UInt21ListA, "UInt21ListAA")
            assert_array_matches(BoolListAA, BoolListA, "BoolListAA")

            assert_array_matches(UInt32ListAB, UInt32ListA, "UInt32ListAB")
            assert_array_matches(Int32ListAB, Int32ListA, "Int32ListAB")
            assert_array_matches(UInt48ListAB, UInt48ListA, "UInt48ListAB")
            assert_array_matches(FloatListAB, FloatListA, "FloatListAB")
            assert_array_matches(DoubleListAB, DoubleListA, "DoubleListAB")
            assert_array_matches(UInt16ListAB, UInt16ListA, "UInt16ListAB")
            assert_array_matches(UInt16Pack0AB, UInt16Pack0A, "UInt16Pack0AB")
            assert_array_matches(UInt16Pack1AB, UInt16Pack1A, "UInt16Pack1AB")
            assert_array_matches(UInt21ListAB, UInt21ListA, "UInt21ListAB")
            assert_array_matches(BoolListAB, BoolListA, "BoolListAB")

            for i in range(32):
                root.RemoteListDevice.UInt32List.set(UInt32ListB[i],index=i)
                root.RemoteListDevice.Int32List.set(Int32ListB[i],index=i)
                root.RemoteListDevice.UInt48List.set(UInt48ListB[i],index=i)
                root.RemoteListDevice.FloatList.set(FloatListB[i],index=i)
                root.RemoteListDevice.DoubleList.set(DoubleListB[i],index=i)
                root.RemoteListDevice.UInt16List.set(UInt16ListB[i],index=i)
                root.RemoteListDevice.UInt16Pack0.set(UInt16Pack0B[i],index=i)
                root.RemoteListDevice.UInt16Pack1.set(UInt16Pack1B[i],index=i)
                root.RemoteListDevice.UInt21List.set(UInt21ListB[i],index=i)
                root.RemoteListDevice.BoolList.set(BoolListB[i],index=i)

            UInt32ListBA  = root.RemoteListDevice.UInt32List.get()
            Int32ListBA   = root.RemoteListDevice.Int32List.get()
            UInt48ListBA  = root.RemoteListDevice.UInt48List.get()
            FloatListBA   = root.RemoteListDevice.FloatList.get()
            DoubleListBA  = root.RemoteListDevice.DoubleList.get()
            UInt16ListBA  = root.RemoteListDevice.UInt16List.get()
            UInt16Pack0BA = root.RemoteListDevice.UInt16Pack0.get()
            UInt16Pack1BA = root.RemoteListDevice.UInt16Pack1.get()
            UInt21ListBA  = root.RemoteListDevice.UInt21List.get()
            BoolListBA    = root.RemoteListDevice.BoolList.get()

            UInt32ListBB  = np.array([0] * 32,np.uint32)
            Int32ListBB   = np.array([0] * 32,np.int32)
            UInt48ListBB  = np.array([0] * 32,np.uint64)
            FloatListBB   = np.array([0] * 32,np.float32)
            DoubleListBB  = np.array([0] * 32,np.float64)
            UInt16ListBB  = np.array([0] * 32,np.uint32)
            UInt16Pack0BB = np.array([0] * 32,np.uint32)
            UInt16Pack1BB = np.array([0] * 32,np.uint32)
            UInt21ListBB  = np.array([0] * 32,np.uint32)
            BoolListBB    = np.array([0] * 32,bool)

            for i in range(32):
                UInt32ListBB[i]  = root.RemoteListDevice.UInt32List.get(index=i)
                Int32ListBB[i]   = root.RemoteListDevice.Int32List.get(index=i)
                UInt48ListBB[i]  = root.RemoteListDevice.UInt48List.get(index=i)
                FloatListBB[i]   = root.RemoteListDevice.FloatList.get(index=i)
                DoubleListBB[i]  = root.RemoteListDevice.DoubleList.get(index=i)
                UInt16ListBB[i]  = root.RemoteListDevice.UInt16List.get(index=i)
                UInt16Pack0BB[i] = root.RemoteListDevice.UInt16Pack0.get(index=i)
                UInt16Pack1BB[i] = root.RemoteListDevice.UInt16Pack1.get(index=i)
                UInt21ListBB[i]  = root.RemoteListDevice.UInt21List.get(index=i)
                BoolListBB[i]    = root.RemoteListDevice.BoolList.get(index=i)

            assert_array_matches(UInt32ListBA, np.array(UInt32ListB, np.uint32), "UInt32ListBA")
            assert_array_matches(Int32ListBA, np.array(Int32ListB, np.int32), "Int32ListBA")
            assert_array_matches(UInt48ListBA, np.array(UInt48ListB, np.uint64), "UInt48ListBA")
            assert_array_matches(FloatListBA, np.array(FloatListB, np.float32), "FloatListBA")
            assert_array_matches(DoubleListBA, np.array(DoubleListB, np.float64), "DoubleListBA")
            assert_array_matches(UInt16ListBA, np.array(UInt16ListB, np.uint16), "UInt16ListBA")
            assert_array_matches(UInt16Pack0BA, np.array(UInt16Pack0B, np.uint16), "UInt16Pack0BA")
            assert_array_matches(UInt16Pack1BA, np.array(UInt16Pack1B, np.uint16), "UInt16Pack1BA")
            assert_array_matches(UInt21ListBA, np.array(UInt21ListB, np.uint32), "UInt21ListBA")
            assert_array_matches(BoolListBA, np.array(BoolListB, bool), "BoolListBA")

            assert_array_matches(UInt32ListBB, np.array(UInt32ListB, np.uint32), "UInt32ListBB")
            assert_array_matches(Int32ListBB, np.array(Int32ListB, np.int32), "Int32ListBB")
            assert_array_matches(UInt48ListBB, np.array(UInt48ListB, np.uint64), "UInt48ListBB")
            assert_array_matches(FloatListBB, np.array(FloatListB, np.float32), "FloatListBB")
            assert_array_matches(DoubleListBB, np.array(DoubleListB, np.float64), "DoubleListBB")
            assert_array_matches(UInt16ListBB, np.array(UInt16ListB, np.uint16), "UInt16ListBB")
            assert_array_matches(UInt16Pack0BB, np.array(UInt16Pack0B, np.uint16), "UInt16Pack0BB")
            assert_array_matches(UInt16Pack1BB, np.array(UInt16Pack1B, np.uint16), "UInt16Pack1BB")
            assert_array_matches(UInt21ListBB, np.array(UInt21ListB, np.uint32), "UInt21ListBB")
            assert_array_matches(BoolListBB, np.array(BoolListB, bool), "BoolListBB")

            root.RemoteListDevice.UInt32List.set(UInt32ListA)
            root.RemoteListDevice.Int32List.set(Int32ListA)

            root.RemoteListDevice.UInt32List.set(np.array([1,2,3],np.uint32),index=7)
            root.RemoteListDevice.Int32List.set([1,-22,-33],index=5)

            resA = root.RemoteListDevice.UInt32List.get()
            resB = root.RemoteListDevice.Int32List.get()

            UInt32ListA[7:10] = [1,2,3]
            Int32ListA[5:8] = [1,-22,-33]

            assert_array_matches(resA, UInt32ListA, "UInt32ListA stripe update")
            assert_array_matches(resB, Int32ListA, "Int32ListA stripe update")

            # Test value shift
            _ = resA[0] >> 5

            root.RemoteListDevice.UInt32List.set(UInt32ListA[::2])
            root.RemoteListDevice.Int32List.set(Int32ListA[::2])

            resA = root.RemoteListDevice.UInt32List.get()
            resB = root.RemoteListDevice.Int32List.get()

            assert_array_matches(resA[:16], UInt32ListA[::2], "UInt32ListA strided prefix")
            assert_array_matches(resB[:16], Int32ListA[::2], "Int32ListA strided prefix")
            assert_array_matches(resA[16:], UInt32ListA[16:], "UInt32ListA untouched suffix")
            assert_array_matches(resB[16:], Int32ListA[16:], "Int32ListA untouched suffix")



def run_gui():
    import pyrogue.pydm

    with RemoteListRoot() as root:
        pyrogue.pydm.runPyDM(root=root,title='test123',sizeX=1000,sizeY=500)

if __name__ == "__main__":
    test_memory()
    #run_gui()
