#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Server only test script
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
import argparse
import test_large


# Set the argument parser
parser = argparse.ArgumentParser('Test Server')

parser.add_argument(
    "--oldGui",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Use old gui",
)

parser.add_argument(
    "--gui",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Use gui",
)

parser.add_argument(
    "--epics3",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Enable EPICS 3",
)

parser.add_argument(
    "--epics4",
    action   = 'store_true',
    required = False,
    default  = False,
    help     = "Enable EPICS 4",
)

# Get the arguments
args = parser.parse_args()

if args.epics3:
    import pyrogue.protocols.epics

if args.epics4:
    import pyrogue.protocols.epicsV4

#rogue.Logging.setFilter('pyrogue.epicsV3.Value',rogue.Logging.Debug)
#rogue.Logging.setLevel(rogue.Logging.Debug)

#logger = logging.getLogger('pyrogue')
#logger.setLevel(logging.DEBUG)


class DummyTree(pyrogue.Root):

    def __init__(self):
        self._scnt = 0
        self._sdata = np.array(0)

        pyrogue.Root.__init__(self,
                              name='dummyTree',
                              description="Dummy tree for example",
                              timeout=2.0,
                              pollEn=True,
                              serverPort=0)

        # Use a memory space emulator
        sim = pyrogue.interfaces.simulation.MemEmulate()
        sim.setName("SimSlave")

        # Add Device
        self.add(test_device.AxiVersion(memBase=sim,
                                        guiGroup='TestGroup',
                                        offset=0x0))
        self.add(test_large.TestLarge(guiGroup='TestGroup'))

        # Add Data Writer
        self._prbsTx = pyrogue.utilities.prbs.PrbsTx()
        self.add(self._prbsTx)
        self._fw = pyrogue.utilities.fileio.StreamWriter()
        self.add(self._fw)
        self._prbsTx >> self._fw.getChannel(0)

        # Add Data Receiver
        drx = pyrogue.DataReceiver()
        self._prbsTx >> drx
        self.add(drx)

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
            value = np.zeros(100,dtype=np.float64)))

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

        if args.epics3:
            self._epics=pyrogue.protocols.epics.EpicsCaServer(base="test", root=self)
            self.addProtocol(self._epics)

        if args.epics4:
            self._epics4=pyrogue.protocols.epicsV4.EpicsPvServer(base="test", root=self,incGroups=None,excGroups=None)
            self.addProtocol(self._epics4)

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
        dummyTree.saveAddressMap('addr_map.csv')
        dummyTree.saveAddressMap('addr_map.h',headerEn=True)

        if args.oldGui:
            import pyrogue.gui
            pyrogue.gui.runGui(root=dummyTree)

        elif args.gui:
            import pyrogue.pydm
            pyrogue.pydm.runPyDM(root=dummyTree,title='test123',sizeX=1000,sizeY=500)

        else:
            pyrogue.waitCntrlC()
