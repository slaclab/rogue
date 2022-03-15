#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# Title      : Example Root
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
import pyrogue.examples
import pyrogue.protocols
import rogue.interfaces.stream
import rogue.interfaces.memory
import rogue
import math
import numpy as np
import pyrogue.protocols.epicsV4
import pickle
import matplotlib.pyplot as plt

try:
    import pyrogue.protocols.epics
except Exception:
    pass

class ExampleRoot(pyrogue.Root):

    def __init__(self,
                 epics3En=False,
                 epics4En=False):

        self._scnt = 0
        self._sdata = np.zeros(100,dtype=np.float64)

        self._fig = None
        pyrogue.Root.__init__(self,
                              description="Example Root",
                              timeout=2.0,
                              pollEn=True,
                              serverPort=0)

        # Use a memory space emulator
        sim = rogue.interfaces.memory.Emulate(4,0x1000)
        sim.setName("SimSlave")
        self.addInterface(sim)

        # Add Device
        self.add(pyrogue.examples.AxiVersion(memBase=sim,
                                        guiGroup='TestGroup',
                                        offset=0x0))
        self.add(pyrogue.examples.LargeDevice(guiGroup='TestGroup'))

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
            disp='{:1.2f}'))
            #value = np.zeros(100,dtype=np.float64)))

        self.add(pyrogue.LinkVariable(
            name = 'TestPlotFigure',
            mode = 'RO',
            dependencies = [self.TestArray],
            linkedGet = self._getPlot))

        if epics3En:
            self._epics=pyrogue.protocols.epics.EpicsCaServer(base="test", root=self)
            self.addProtocol(self._epics)

        if epics4En:
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

    def _getPlot(self, read):

        if self._fig is not None:
            plt.close(self._fig)

        self._fig, ax = plt.subplots()
        ax.plot(self.TestArray.get(read=read))
        return self._fig
