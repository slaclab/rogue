#-----------------------------------------------------------------------------
# This file is part of the rogue_example software. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue_example software, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr
import rogue
import rogue.interfaces.memory as rim

from conftest import MemoryRoot

#rogue.Logging.setLevel(rogue.Logging.Debug)

class SimpleVarDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name      = 'Var1',
            offset    =  0x0,
            bitSize   = 32,
            bitOffset = 0,
        ))

        self.add(pr.RemoteVariable(
            name      = 'Var2',
            offset    =  0x4,
            bitSize   = 32,
            bitOffset = 0,
        ))

class BlockDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        numRegs = 16

        self.add(pr.RemoteVariable(
            name         = "DataBlock",
            description  = "Large Data Block",
            offset       = 0,
            bitOffset    = 0,
            numValues    = numRegs,
            valueBits    = 32,
            valueStride  = 32,
            bulkOpEn     = False,
            overlapEn    = True,
            verify       = False,
            hidden       = True,
            base         = pr.UInt,
            mode         = "RW",
        ))

        for i in range(numRegs//2):
            self.add(pr.RemoteVariable(
                name        = f'DataVar[{i}]',
                description = f'Data Value {i}',
                offset      = i * 4,
                bitOffset   = 0,
                bitSize     = 32,
                disp        = '0x{:x}',
                mode        = 'RW',
                overlapEn   = True,
            ))

        self.add(pr.RemoteVariable(
            name         = "ListVar",
            description  = "List Variable",
            offset       = (numRegs//2)*4,
            bitOffset    = 0,
            numValues    = numRegs//2,
            valueBits    = 32,
            valueStride  = 32,
            overlapEn    = True,
            disp         = '0x{:x}',
            base         = pr.UInt,
            mode         = "RW",
        ))

        @self.command(description='Load the Config')
        def LoadConfig(arg):

            for i in range(numRegs):
                self.DataBlock.set(value=i, index=i, write=False)

            self.writeAndVerifyBlocks()

class BlockRoot(pr.Root):

    def __init__(self):
        pr.Root.__init__(self,
                         name='BlockRoot',
                         description="Dummy tree for example",
                         timeout=2.0,
                         pollEn=False)

        # Use a memory space emulator
        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        self.addInterface(sim)

        self.add(BlockDevice(
            offset     = 0x0000,
            memBase    = sim,
        ))

        self.add(SimpleVarDevice(
            offset     = 0xF034, # non-4kB aligned base offset
            memBase    = sim,
        ))

def test_block():

    with BlockRoot() as root:

        root.BlockDevice.LoadConfig()

        setVal = 0x55555

        root.BlockDevice.DataVar[4].set(setVal)
        root.BlockDevice.ListVar.set(setVal,index=4)

        if setVal != root.BlockDevice.DataVar[4].value():
            raise AssertionError('Read error detected after value!')

        if setVal != root.BlockDevice.DataVar[4].get():
            raise AssertionError('Read error detected after get!')

        if setVal != root.BlockDevice.ListVar.get(index=4):
            raise AssertionError('Read error detected after index get!')

        root.BlockDevice.readBlocks()

        if setVal != root.BlockDevice.DataVar[4].get():
            raise AssertionError('Read error detected after read then get!')

        if setVal != root.BlockDevice.ListVar.get(index=4):
            raise AssertionError('Read error detected after read then index get!')


class CustomBlockDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Pre-made block covering the first two registers
        self.addCustomBlock(rim.Block(0x0, 8))

        self.add(pr.RemoteVariable(
            name    = 'Inner0',
            offset  = 0x0,
            bitSize = 32,
            base    = pr.UInt,
        ))

        self.add(pr.RemoteVariable(
            name    = 'Inner1',
            offset  = 0x4,
            bitSize = 32,
            base    = pr.UInt,
        ))

        self.add(pr.RemoteVariable(
            name    = 'Outer',
            offset  = 0x10,
            bitSize = 32,
            base    = pr.UInt,
        ))

class CustomBlockRoot(MemoryRoot):
    def __init__(self):
        super().__init__(name='CustomBlockRoot')
        self.add(CustomBlockDevice(name='Dev', offset=0x0, memBase=self._mem))

def test_custom_block_wired():

    with CustomBlockRoot() as root:
        dev = root.Dev

        assert dev.Inner0._block is not None
        assert dev.Inner0._block is dev.Inner1._block
        assert dev.Outer._block is not None
        assert dev.Outer._block is not dev.Inner0._block
        assert len(dev._blocks) == 2

        dev.Inner0.set(0x11223344)
        dev.Inner1.set(0x55667788)
        dev.Outer.set(0x99AABBCC)
        dev.readBlocks()

        assert dev.Inner0.get() == 0x11223344
        assert dev.Inner1.get() == 0x55667788
        assert dev.Outer.get() == 0x99AABBCC


if __name__ == "__main__":
    test_block()
    test_custom_block_wired()
