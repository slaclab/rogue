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
import pytest

pytestmark = pytest.mark.integration

class EnumTransportDevice(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name         = 'Config',
            description  = 'ENUM Test Field',
            offset       = 0x0,
            bitSize      = 4,
            bitOffset    = 0,
            mode         = 'RW',
            enum         = {
                0: 'Config2', # 0 maps to 2
                1: 'Config1', # 1 maps to 1
                2: 'Config0', # 2 maps to 0
            },
        ))

        self.add(pr.LocalVariable(
            name         = 'Status',
            description  = 'ENUM Test Field',
            offset       = 0x4,
            bitSize      = 4,
            bitOffset    = 0,
            mode         = 'RO',
            value        = 3, # Testing undef enum
            enum         = {
                0: 'Status0',
                1: 'Status1',
                2: 'Status2',
            },
        ))

class EnumTransportRoot(pr.Root):
    def __init__(self, *, port):
        super().__init__(name='dummyTree', description="Dummy tree for example", timeout=2.0, pollEn=False)

        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        self.addInterface(sim)

        ms = rogue.interfaces.memory.TcpServer("127.0.0.1", port)
        self.addInterface(ms)
        sim << ms

        mc = rogue.interfaces.memory.TcpClient("127.0.0.1", port, True)
        self.memClient = mc
        self.addInterface(mc)

        # Exercise enum conversion over the real TCP memory transport.
        self.add(EnumTransportDevice(
            name       = 'Dev',
            offset     = 0x0,
            memBase    = mc,
        ))


def test_enum(free_tcp_port):
    with EnumTransportRoot(port=free_tcp_port) as root:
        for i in range(3):
            root.Dev.Config.setDisp(f'Config{i}')
            assert root.Dev.Config.get() == (2 - i)

        assert root.Dev.Status.getDisp() == 'INVALID: 3'

if __name__ == "__main__":
    test_enum()
