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
import pyrogue.utilities.prbs
import rogue.interfaces.stream
import test_device
import time
import rogue
import pyrogue.protocols
import logging
import math
import numpy as np

#import pyrogue.pydm

#rogue.Logging.setFilter('pyrogue.epicsV3.Value',rogue.Logging.Debug)
#rogue.Logging.setLevel(rogue.Logging.Debug)

#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)


class DummyTree(pyrogue.Root):

    def __init__(self):
        self._scnt = 0
        self._sdata = np.array(0)

        pyrogue.Root.__init__(self,name='dummyTree',description="Dummy tree for example")

        # Use a memory space emulator
        sim = pyrogue.interfaces.simulation.MemEmulate()
        
        # Add Device
        self.add(test_device.AxiVersion(memBase=sim,offset=0x0))

        # Add Data Writer
        self.add(pyrogue.utilities.fileio.StreamWriter())

        # Add Run Control
        self.add(pyrogue.RunControl())

        # Add process controller
        p = pyrogue.Process()
        p.add(pyrogue.LocalVariable(name='Test1',value=''))
        p.add(pyrogue.LocalVariable(name='Test2',value=''))
        self.add(p)

        #self.AxiVersion.AlarmTest.addToGroup('NoServe')

        self.add(pyrogue.LocalVariable(
            name = 'TestPlot',
            mode = 'RO',
            pollInterval=1.0,
            localGet = self._mySin,
            minimum=-1.0,
            maximum=1.0,
            disp='{:1.2f}',
            value = 0.0))

        self.add(pyrogue.LocalVariable(
            name = 'TestXAxis',
            mode = 'RO',
            pollInterval=1.0,
            localGet = self._myXAxis,
            disp='{:1.2f}',
            value = 1.0))

        self.add(pyrogue.LocalVariable(
            name = 'TestArray',
            mode = 'RO',
            pollInterval=1.0,
            localGet = self._myArray,
            disp='{:1.2f}',
            value = np.array(0)))

        #self.add(pyrogue.LocalVariable(
        #    name = 'Test/Slash',
        #    mode = 'RW',
        #    value = ''))

        #self.add(pyrogue.LocalVariable(
        #    name = 'Test.Dot',
        #    mode = 'RW',
        #    value = ''))

        #self.add(pyrogue.LocalVariable(
        #    name = 'Test\BackSlash',
        #    mode = 'RW',
        #    value = ''))

        #self.add(pyrogue.LocalVariable(
        #    name = 'Test&And',
        #    mode = 'RW',
        #    value = ''))

        #self.rudpServer = pyrogue.protocols.UdpRssiPack(
        #    name    = 'UdpServer',
        #    port    = 8192,
        #    jumbo   = True,
        #    server  = True,
        #    expand  = False,
        #    )
        #self.add(self.rudpServer)

        # Create the ETH interface @ IP Address = args.dev
        #self.rudpClient = pyrogue.protocols.UdpRssiPack(
        #    name    = 'UdpClient',
        #    host    = "127.0.0.1",
        #    port    = 8192,
        #    jumbo   = True,
        #    expand  = False,
        #    )
        #self.add(self.rudpClient)

        #self.prbsTx = pyrogue.utilities.prbs.PrbsTx()
        #self.add(self.prbsTx)

        #pyrogue.streamConnect(self.prbsTx,self.rudpClient.application(0))

        # Start the tree with pyrogue server, internal nameserver, default interface
        # Set pyroHost to the address of a network interface to specify which nework to run on
        # set pyroNs to the address of a standalone nameserver (startPyrorNs.py)
        #self.start(timeout=2.0, pollEn=True, serverPort=9099, sqlUrl='sqlite:///test.db')
        self.start(timeout=2.0, pollEn=True, serverPort=0, sqlUrl='sqlite:///test.db')

        #self.epics=pyrogue.protocols.epics.EpicsCaServer(base="test", root=self)
        #self.epics.start()

        #self.epics4=pyrogue.protocols.epicsV4.EpicsPvServer(base="test", root=self)
        #self.epics4.start()

    def _mySin(self):
        val = math.sin(2*math.pi*self._scnt / 100)
        self._sdata = np.append(self._sdata,val)
        self._scnt += 1
        return val

    def _myXAxis(self):
        return float(self._scnt)

    def _myArray(self):
        return self._sdata

if __name__ == "__main__":

    with DummyTree() as dummyTree:
        pyrogue.waitCntrlC()
        #pyrogue.pydm.runPyDM(root=dummyTree)

