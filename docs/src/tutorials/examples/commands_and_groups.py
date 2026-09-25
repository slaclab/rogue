#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       Commands, Blocks and Groups tutorial: the three command flavours, how
#       Variables pack into Blocks, and how Groups filter bulk operations.
#
#       Runs with no hardware. This file is included into
#       docs/src/tutorials/commands_and_groups.rst and is exercised by
#       tests/docs/test_docs_tutorial_examples.py.
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


class CommandDevice(pr.Device):
    """All three command flavours on one Device.

    ``RemoteCommand`` writes to hardware, the ``@self.command`` decorator runs
    arbitrary Python, and ``LocalCommand`` wraps a plain callable that returns
    a value.
    """

    def __init__(self, **kwargs):
        super().__init__(description='Commands demonstration', **kwargs)

        self.add(pr.RemoteVariable(
            name        = 'Control',
            description = 'Control register written by commands',
            offset      = 0x00,
            bitSize     = 32,
            base        = pr.UInt,
            mode        = 'RW',
            disp        = '{:#010x}'))

        # A RemoteCommand writes a value to an address. ``post()`` fires the
        # write without waiting for a response, which is what you want for a
        # self-clearing trigger bit.
        self.add(pr.RemoteCommand(
            name        = 'Pulse',
            description = 'Strobe a self-clearing trigger bit',
            offset      = 0x10,
            bitSize     = 1,
            base        = pr.UInt,
            function    = lambda cmd: cmd.post(1)))

        # The decorator form is the shortest way to attach a procedure that
        # touches several Variables. ``arg`` carries the caller's value.
        @self.command(value=0, description='Write an arbitrary Control value')
        def SetControl(arg):
            self.Control.set(int(arg))

        # A LocalCommand touches no registers at all. Use it for host-side
        # helpers that report something back.
        self.add(pr.LocalCommand(
            name        = 'Describe',
            description = 'Return a host-side summary string',
            function    = lambda: 'CommandDevice ready',
            retValue    = ''))


class PackedDevice(pr.Device):
    """Three fields sharing one 32-bit register.

    Because all three use ``offset=0x00`` and differ only in ``bitOffset``,
    PyRogue coalesces them into a single ``Block`` -- so setting all three
    costs one memory transaction, not three.
    """

    def __init__(self, **kwargs):
        super().__init__(description='Three fields, one register', **kwargs)

        for name, bitOffset in (('Low', 0), ('Middle', 8), ('High', 16)):
            self.add(pr.RemoteVariable(
                name      = name,
                offset    = 0x00,
                bitSize   = 8,
                bitOffset = bitOffset,
                base      = pr.UInt,
                mode      = 'RW',
                disp      = '{:#04x}'))


class SpreadDevice(pr.Device):
    """The same three fields at separate addresses, for contrast.

    Identical API, but each Variable now owns a Block of its own, so the same
    three writes become three transactions.
    """

    def __init__(self, **kwargs):
        super().__init__(description='Three fields, three registers', **kwargs)

        for index, name in enumerate(('Low', 'Middle', 'High')):
            self.add(pr.RemoteVariable(
                name    = name,
                offset  = index * 4,
                bitSize = 8,
                base    = pr.UInt,
                mode    = 'RW',
                disp    = '{:#04x}'))


class GroupDevice(pr.Device):
    """Variables tagged with Groups so bulk operations can skip them.

    Groups are labels, not access control. Bulk operations such as
    ``getYaml()`` accept ``incGroups``/``excGroups`` and honour them; nothing
    stops a direct ``.get()`` on a tagged Variable.
    """

    def __init__(self, **kwargs):
        super().__init__(description='Groups demonstration', **kwargs)

        self.add(pr.RemoteVariable(
            name='Saved', offset=0x00, bitSize=32,
            base=pr.UInt, mode='RW'))

        # 'NoConfig' is the convention for values that should not be captured
        # in a saved configuration -- counters, status, scratch registers.
        volatile = pr.RemoteVariable(
            name='Volatile', offset=0x04, bitSize=32,
            base=pr.UInt, mode='RW')
        self.add(volatile)
        volatile.addToGroup('NoConfig')

        # 'NoServe' keeps a value out of EPICS and other servers by default.
        private = pr.RemoteVariable(
            name='Private', offset=0x08, bitSize=32,
            base=pr.UInt, mode='RW')
        self.add(private)
        private.addToGroup('NoServe')


class TutorialRoot(pr.Root):
    """Hosts every Device above against one emulated memory space."""

    def __init__(self, **kwargs):
        super().__init__(description='Commands, Blocks and Groups',
                         timeout=2.0, **kwargs)

        self._sim = rogue.interfaces.memory.Emulate(4, 0x10000)
        self._sim.setName('SimSlave')
        self.addInterface(self._sim)

        self.add(CommandDevice(name='Cmds', memBase=self._sim, offset=0x0000))
        self.add(PackedDevice(name='Packed', memBase=self._sim, offset=0x1000))
        self.add(SpreadDevice(name='Spread', memBase=self._sim, offset=0x2000))
        self.add(GroupDevice(name='Groups', memBase=self._sim, offset=0x3000))


if __name__ == '__main__':
    with TutorialRoot() as root:
        print('--- Commands')
        root.Cmds.Pulse()
        root.Cmds.SetControl(0x55)
        print('   Control after SetControl :', root.Cmds.Control.valueDisp())
        print('   Describe returned        :', root.Cmds.Describe())

        print('--- Blocks')
        root.Packed.Low.set(0xAA)
        root.Packed.Middle.set(0xBB)
        root.Packed.High.set(0xCC)
        print('   packed values  :',
              root.Packed.Low.valueDisp(),
              root.Packed.Middle.valueDisp(),
              root.Packed.High.valueDisp())
        print('   Blocks used by Packed (offset 0x00 x3) :',
              len(root.Packed._blocks))
        print('   Blocks used by Spread (0x00/0x04/0x08) :',
              len(root.Spread._blocks))

        print('--- Groups')
        root.Groups.Saved.set(1)
        root.Groups.Volatile.set(2)
        root.Groups.Private.set(3)

        everything = root.getYaml(readFirst=False, modes=['RW'],
                                  incGroups=None, excGroups=None)
        config = root.getYaml(readFirst=False, modes=['RW'],
                              incGroups=None, excGroups=['NoConfig'])

        print('   Saved in full dump      :', 'Saved' in everything)
        print('   Volatile in full dump   :', 'Volatile' in everything)
        print('   Volatile in saved config:', 'Volatile' in config)
        print('   Volatile groups         :', root.Groups.Volatile.groups)
