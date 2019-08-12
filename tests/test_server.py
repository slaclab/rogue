#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Server only test script
#-----------------------------------------------------------------------------
# File       : test_server.py
# Created    : 2018-02-28
#-----------------------------------------------------------------------------
# This file is part of the rogue_example software. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue_example software, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import pyrogue
import pyrogue.interfaces.simulation
import pyrogue.utilities.fileio
import rogue.interfaces.stream
import test_device
import time
import rogue
import pyrogue.protocols.epics
import logging

#rogue.Logging.setFilter('pyrogue.epicsV3.Value',rogue.Logging.Debug)
#rogue.Logging.setLevel(rogue.Logging.Debug)

#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)

class DummyTree(pyrogue.Root):

    def __init__(self):

        pyrogue.Root.__init__(self,name='dummyTree',description="Dummy tree for example")

        # Use a memory space emulator
        sim = pyrogue.interfaces.simulation.MemEmulate()
        
        # Add Device
        self.add(test_device.AxiVersion(memBase=sim,offset=0x0))

        # Add Data Writer
        self.add(pyrogue.utilities.fileio.StreamWriter())

        # Start the tree with pyrogue server, internal nameserver, default interface
        # Set pyroHost to the address of a network interface to specify which nework to run on
        # set pyroNs to the address of a standalone nameserver (startPyrorNs.py)
        self.start(timeout=2.0, pollEn=True, zmqPort=9099)

        self.epics=pyrogue.protocols.epics.EpicsCaServer(base="test", root=self)
        self.epics.start()

if __name__ == "__main__":

    with DummyTree() as dummyTree:

        print("Running in python main")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            exit()

