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

class EnumDev(pr.Device):

    def __init__(self,**kwargs):

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

        self.add(pr.RemoteVariable(
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

class DummyTree(pr.Root):

    def __init__(self):
        pr.Root.__init__(self,
                         name='dummyTree',
                         description="Dummy tree for example",
                         timeout=2.0,
                         pollEn=False,
                         serverPort=None)

        # Use a memory space emulator
        sim = pr.interfaces.simulation.MemEmulate()
        self.addInterface(sim)

        # Create a memory gateway
        ms = rogue.interfaces.memory.TcpServer("127.0.0.1",9080);
        self.addInterface(ms)

        # Connect the memory gateways together
        sim << ms

        # Create a memory gateway
        mc = rogue.interfaces.memory.TcpClient("127.0.0.1",9080);
        self.addInterface(mc)

        # Add Device
        self.add(EnumDev(
            name       = 'Dev',
            offset     = 0x0,
            memBase    = mc,
        ))

def test_enum():

    with DummyTree() as root:

        for i in range(3):
            root.Dev.Config.setDisp(f'Config{i}')
            config =  root.Dev.Config.get()
            if ( config != (2-i) ):
                raise AssertionError( f'root.Dev.config.get()={config}' )

        # Test the undef enum case
        status = root.Dev.Status.getDisp()
        if ( status != 'INVALID: 3'):
            raise AssertionError( f'root.Dev.Status.getDisp()={status}' )

if __name__ == "__main__":
    test_enum()
