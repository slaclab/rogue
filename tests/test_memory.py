#!/usr/bin/env python

# Comment added by rherbst for demonstration purposes.
import datetime
import parse
import pyrogue as pr
import pyrogue.interfaces.simulation
import rogue.interfaces.memory
import time

rogue.Logging.setLevel(rogue.Logging.Debug)
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

class DummyTree(pr.Root):

    def __init__(self):
        pr.Root.__init__(self,name='dummyTree',description="Dummy tree for example")

        # Use a memory space emulator
        self.sim = pr.interfaces.simulation.MemEmulate()

        # Create a memory gateway
        self.ms = rogue.interfaces.memory.TcpServer("127.0.0.1",9020);
        pr.busConnect(self.ms,self.sim)

        # Create a memory gateway
        self.mc = rogue.interfaces.memory.TcpClient("127.0.0.1",9020);

        # Add Device
        self.add(AxiVersion(memBase=self.mc,offset=0x0))

        # Start the tree with pyrogue server, internal nameserver, default interface
        # Set pyroHost to the address of a network interface to specify which nework to run on
        # set pyroNs to the address of a standalone nameserver (startPyrorNs.py)
        self.start(timeout=2.0, pyroGroup='testGroup', pyroAddr=None, pyroNsAddr=None)


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

if __name__ == "__main__":
    test_memory()

