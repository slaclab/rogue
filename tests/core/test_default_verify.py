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
import rogue.interfaces.memory as rim


class RecordingMemory(rim.Slave):
    def __init__(self):
        super().__init__(4, 0x1000)
        self.transactions = []
        self.data = bytearray(0x1000)

    def _doTransaction(self, transaction):
        address = transaction.address()
        size = transaction.size()
        transaction_type = transaction.type()
        self.transactions.append(transaction_type)

        if transaction_type in (rim.Write, rim.Post):
            data = bytearray(size)
            transaction.getData(data, 0)
            self.data[address:address + size] = data
        else:
            transaction.setData(self.data[address:address + size], 0)

        transaction.done()


class VerifyLeaf(pr.Device):
    def __init__(self, *, memBase=None, **kwargs):
        super().__init__(memBase=memBase, **kwargs)
        self.add(pr.RemoteVariable(
            name='Inherited',
            offset=0x0,
            bitSize=32,
            mode='RW',
        ))


class VerifyDevice(pr.Device):
    def __init__(self, *, memBase, **kwargs):
        super().__init__(memBase=memBase, **kwargs)

        self.add(pr.RemoteVariable(
            name='Inherited',
            offset=0x0,
            bitSize=32,
            mode='RW',
        ))

        self.add(pr.RemoteVariable(
            name='ExplicitOn',
            offset=0x4,
            bitSize=32,
            mode='RW',
            verify=True,
        ))

        self.add(pr.RemoteVariable(
            name='ExplicitOff',
            offset=0x8,
            bitSize=32,
            mode='RW',
            verify=False,
        ))

        self.add(VerifyLeaf(
            name='Child',
            offset=0x10,
        ))


class VerifyRoot(pr.Root):
    def __init__(self, *, defaultVerify=True):
        super().__init__(name='VerifyRoot', pollEn=False, defaultVerify=defaultVerify)
        self.memory = RecordingMemory()
        self.addInterface(self.memory)
        self.add(VerifyDevice(name='InheritedDevice', memBase=self.memory))
        self.add(VerifyDevice(name='EnabledDevice', memBase=self.memory, offset=0x100, defaultVerify=True))
        self.add(VerifyDevice(name='DisabledDevice', memBase=self.memory, offset=0x200, defaultVerify=False))


def test_root_and_device_verify_defaults_follow_override_precedence():
    with VerifyRoot(defaultVerify=False) as root:
        assert root.InheritedDevice.Inherited.verifyEn is False
        assert root.InheritedDevice.ExplicitOn.verifyEn is True
        assert root.InheritedDevice.ExplicitOff.verifyEn is False
        assert root.InheritedDevice.Child.Inherited.verifyEn is False

        assert root.EnabledDevice.Inherited.verifyEn is True
        assert root.EnabledDevice.Child.Inherited.verifyEn is True
        assert root.DisabledDevice.Inherited.verifyEn is False
        assert root.DisabledDevice.Child.Inherited.verifyEn is False


def test_default_verify_true_preserves_existing_behavior():
    with VerifyRoot() as root:
        assert root.InheritedDevice.Inherited.verifyEn is True
        assert root.InheritedDevice.ExplicitOff.verifyEn is False
        assert root.DisabledDevice.Inherited.verifyEn is False


def test_inherited_verify_default_controls_readback_transactions():
    with VerifyRoot(defaultVerify=False) as root:
        root.memory.transactions.clear()
        root.InheritedDevice.Inherited.set(1)
        assert root.memory.transactions == [rim.Write]

        root.memory.transactions.clear()
        root.InheritedDevice.ExplicitOn.set(2)
        assert root.memory.transactions == [rim.Write, rim.Verify]
