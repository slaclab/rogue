.. _full_root_definition:

========================================
Review The Complete Root Example
========================================

The full example Root is collected in one listing here so you can compare it
against your implementation and copy from a complete reference.

.. code-block:: python

    class ExampleRoot(pr.Root):

        def __init__(self, epics4En=False):
            self._scnt = 0
            self._sdata = np.zeros(100,dtype=np.float64)

            self._fig = None
            self._ax = None
            pr.Root.__init__(self,
                                description="Example Root",
                                timeout=2.0,
                                pollEn=True)

            # Use a memory space emulator
            sim = rogue.interfaces.memory.Emulate(4,0x1000)
            sim.setName("SimSlave")
            self.addInterface(sim)

            # Add Device
            self.add(pr.examples.AxiVersion(memBase=sim,
                                                guiGroup='TestGroup',
                                                offset=0x0))
            self.add(pr.examples.LargeDevice(guiGroup='TestGroup'))

            # Create configuration stream
            stream = pr.interfaces.stream.Variable(root=self)

            # PRBS Transmitter
            self._prbsTx = pr.utilities.prbs.PrbsTx()
            self.add(self._prbsTx)

            # Add Data Writer, configuration goes to channel 1
            self._fw = pr.utilities.fileio.StreamWriter(configStream={1: stream},rawMode=True)
            self.add(self._fw)
            self._prbsTx >> self._fw.getChannel(0)

            # Data Receiver
            drx = pr.DataReceiver()
            self._prbsTx >> drx
            self.add(drx)

            # Add Run Control
            self.add(pr.RunControl())

            # Add zmq server
            self.zmqServer = pr.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=0)
            self.addInterface(self.zmqServer)

            # Add process controller
            p = pr.Process()
            p.add(pr.LocalVariable(name='Test1',value=''))
            p.add(pr.LocalVariable(name='Test2',value=''))
            self.add(p)

            #self.AxiVersion.AlarmTest.addToGroup('NoServe')

            self.add(pr.LocalVariable(
                name = 'TestPlot',
                mode = 'RO',
                pollInterval=1.0,
                localGet = self._mySin,
                minimum=-1.0,
                maximum=1.0,
                disp='{:1.2f}',
                value = 0.0))

            self.add(pr.LocalVariable(
                name = 'TestXAxis',
                mode = 'RO',
                pollInterval=1.0,
                localGet = self._myXAxis,
                disp='{:1.2f}',
                value = 1.0))

            self.add(pr.LocalVariable(
                name = 'TestArray',
                mode = 'RO',
                pollInterval=1.0,
                localGet = self._myArray,
                disp='{:1.2f}'))
                #value = np.zeros(100,dtype=np.float64)))

            self.add(pr.LinkVariable(
                name = 'TestPlotFigure',
                mode = 'RO',
                dependencies = [self.TestArray],
                linkedGet = self._getPlot))

            if epics4En:
                self._epics4=pr.protocols.epicsV4.EpicsPvServer(base="test", root=self,incGroups=None,excGroups=None)
                self.addProtocol(self._epics4)

            # Remote memory command slave example
            osSlave = pr.examples.OsMemSlave()
            osSlave.setName("OsSlave")
            self.addInterface(osSlave)
            self.add(pr.examples.OsMemMaster(memBase=osSlave))
