.. _tutorials_p_t_root:

===========================
Basic Pyrogue Tree Tutorial
===========================

In this tutorial, we will go through all of the steps creating a pyrogue tree.

Creating a Root Node
====================

The first step is to create the :ref:`Root <pyrogue_tree_node_root>` Node, which is the base Node of the tree.
In order to do this, we need to create the subclass of Root, including calling the Root node. 

Define the init function
------------------------

#. Create the subclass of Root (ExampleRoot)
#. Define needed specialized parameters(_sdata, _fig, _ax)
#. Call the :py:meth:`Root.__init__ <pyrogue.Root.__init__>`
#. Create the :ref:`memory emulater <interfaces_simulation_mememulate>`.
#. Add devices (see :ref:`AxiVersion <tutorials_p_t_device>` for an example device class)
#. Create configuration stream :ref:`Variable <interfaces_python_memory_variable>`
#. Create :ref:`ppg <hardware_pgp_pgp_cardp>` card :ref:`interfaces <interfaces>`
#. Create PRBS Transmitter :ref:`pyrogue_tree_node_device_prbsrx` device
#. Create a :ref:`Stream Writer <pyrogue_tree_node_device_streamwriter>` device
#. Create a :ref:`Data Receiver <pyrogue_tree_node_device_datareceiver>` device
#. Create a :ref:`Run Control <pyrogue_tree_node_device_runcontrol>` device
#. Create a :ref:`ZMQ Server <interfaces_python_zmqserver>` interface
#. Add a :ref:`Process Controller <pyrogue_tree_node_device_process>`
#. Create :ref:`Link <pyrogue_tree_node_variable_link_variable>` and :ref:`Local <pyrogue_tree_node_variable_local_variable>` variables
#. Connect it to the :ref:`EPICS Protocol <pyrogue_protocol_epicspvserver>` class
#. Create and connect memory commands using the built in :ref:`slave <_interfaces_python_os_command_memory_slave>` and custom :ref:`master <interfaces_python_osmemmaster>`

.. code-block:: python

    class ExampleRoot(pyrogue.Root):

        def __init__(self, epics4En=False):
            self._scnt = 0
            self._sdata = np.zeros(100,dtype=np.float64)

            self._fig = None
            self._ax = None
            pyrogue.Root.__init__(self,
                                description="Example Root",
                                timeout=2.0,
                                pollEn=True)

            # Use a memory space emulator
            sim = rogue.interfaces.memory.Emulate(4,0x1000)
            sim.setName("SimSlave")
            self.addInterface(sim)

            # Add Device
            self.add(pyrogue.examples.AxiVersion(memBase=sim,
                                                guiGroup='TestGroup',
                                                offset=0x0))
            self.add(pyrogue.examples.LargeDevice(guiGroup='TestGroup'))

            # Create configuration stream
            stream = pyrogue.interfaces.stream.Variable(root=self)

            # PRBS Transmitter
            self._prbsTx = pyrogue.utilities.prbs.PrbsTx()
            self.add(self._prbsTx)

            # Add Data Writer, configuration goes to channel 1
            self._fw = pyrogue.utilities.fileio.StreamWriter(configStream={1: stream},rawMode=True)
            self.add(self._fw)
            self._prbsTx >> self._fw.getChannel(0)

            # Data Receiver
            drx = pyrogue.DataReceiver()
            self._prbsTx >> drx
            self.add(drx)

            # Add Run Control
            self.add(pyrogue.RunControl())

            # Add zmq server
            self.zmqServer = pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=0)
            self.addInterface(self.zmqServer)

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

            if epics4En:
                self._epics4=pyrogue.protocols.epicsV4.EpicsPvServer(base="test", root=self,incGroups=None,excGroups=None)
                self.addProtocol(self._epics4)

            # Remote memory command slave example
            osSlave = pyrogue.examples.OsMemSlave()
            osSlave.setName("OsSlave")
            self.addInterface(osSlave)
            self.add(pyrogue.examples.OsMemMaster(memBase=osSlave))


Override Necessary Functions
----------------------------

.. code-block:: python

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
            self._fig.clf()
            del self._ax, self._fig

        self._fig = plt.Figure()
        self._ax = self._fig.add_subplot(111)
        self._ax.plot(self.TestArray.get(read=read))
        return self._fig

