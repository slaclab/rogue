.. _pyrogue_tree_node_root:

====
Root
====

The :py:class:`pyrogue.Root` class is the top-level node in a PyRogue tree.
It owns the application lifecycle, coordinates bulk read/write operations,
manages background workers (poll and update), and provides APIs for YAML
save/load and external listeners.

For polling internals and usage patterns, see
:ref:`pyrogue_tree_root_poll_queue`.

Most user applications define a subclass of ``pyrogue.Root`` and add devices
inside ``__init__``.

In practice, ``Root`` is also where hardware connections are usually created and
bound into the tree. A typical pattern is:

* create a memory interface (for example AXI PCIe, TCP simulation, etc.)
* register it with :py:meth:`pyrogue.Root.addInterface`
* pass that interface as ``memBase`` when adding top-level devices
* optionally add management/control interfaces (such as ZMQ) to the same root

.. code-block:: python

   import pyrogue as pr
   import rogue
   import pyrogue.interfaces
   import axipcie

   class EvalBoard(pr.Root):
       def __init__(self, dev='/dev/datadev_0', sim=False, **kwargs):
           super().__init__(name='EvalBoard', description='Evaluation board root', **kwargs)

           # Create the memory-mapped hardware/simulation interface.
           if sim:
               self.memMap = rogue.interfaces.memory.TcpClient('localhost', 11000)
           else:
               self.memMap = rogue.hardware.axi.AxiMemMap(dev)

           # Register memory interface with Root so tree transactions route correctly.
           self.addInterface(self.memMap)

           # Optional management API for GUIs/remote clients.
           self.zmqServer = pyrogue.interfaces.ZmqServer(
               root=self,
               addr='127.0.0.1',
               port=0,
           )
           self.addInterface(self.zmqServer)

           # Add top-level devices and bind them to the same memory interface.
           self.add(axipcie.AxiPcieCore(
               offset=0x00000000,
               memBase=self.memMap,
               expand=True,
           ))

Key Attributes
--------------

Along with inherited :ref:`Node <pyrogue_tree_node>` attributes, root adds:

* ``running``: ``True`` when :py:meth:`pyrogue.Root.start` has been called.
* system commands and variables that support whole-tree control
  (see sections below).

Key Methods
-----------

* :py:meth:`pyrogue.Root.start`
* :py:meth:`pyrogue.Root.stop`
* :py:meth:`pyrogue.Root.addVarListener`
* :py:meth:`pyrogue.Root.getNode`
* :py:meth:`pyrogue.Root.saveYaml`
* :py:meth:`pyrogue.Root.loadYaml`
* :py:meth:`pyrogue.Root.setYaml`
* :py:meth:`pyrogue.Root.pollBlock`

``getNode`` resolves dotted paths such as ``EvalBoard.AxiVersion.ScratchPad``.

Temporarily Blocking Polling
----------------------------

Use :py:meth:`pyrogue.Root.pollBlock` when you need a short critical section
that should not race with background poll reads.

.. code-block:: python

   with root.pollBlock():
       root.MyDevice.SomeControl.set(1)
       root.MyDevice.OtherControl.set(0)

ZmqServer Interface
-------------------

:py:class:`pyrogue.interfaces.ZmqServer` exposes the root over a ZeroMQ control
channel used by tools such as PyDM-based GUIs and external clients.

Common initialization pattern in ``Root.__init__``:

* create server: ``pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=0)``
* add to root with :py:meth:`pyrogue.Root.addInterface`

Notes:

* ``port=0`` auto-selects the first available base port starting at ``9099``
  (the server then uses ``base``, ``base+1``, and ``base+2``)
* binding to ``127.0.0.1`` keeps the server local to the host
* non-local deployments can bind to another interface/address as needed

Yaml File Configuration
-----------------------

Saving and Restoring Configurations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

System-wide state/configuration can be exported to YAML text/files and loaded
back with:

* :py:meth:`pyrogue.Node.getYaml` (Note: inherited from :py:class:`pyrogue.Node` class.)
* :py:meth:`pyrogue.Root.setYaml`
* :py:meth:`pyrogue.Root.saveYaml`
* :py:meth:`pyrogue.Root.loadYaml`

Built-in Groups
^^^^^^^^^^^^^^^

PyRogue root-level configuration/state commands use group filtering to include or exclude
variables and commands from bulk operations.

Common built-in group names:

* ``NoConfig``: excluded from configuration save/load operations.
* ``NoState``: excluded from state snapshot/export operations.
* ``Hidden``: hidden from normal GUI views unless explicitly included.

See :ref:`pyrogue_tree_node_groups` for full built-in group behavior and filtering semantics.

Configuration Array Matching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
YAML load supports node-array style matching and slicing.
For example:

* AmcCard[0] - DacEnable[0], DacEnable[1]
* AmcCard[1] - DacEnable[0], DacEnable[1]
* AmcCard[2] - DacEnable[0], DacEnable[1]

Use Python-like slicing and wildcards:

* Enable DAC channel 0 in all cards:


  * ``AmcCard[:]:DacEnable[0]: True``

* Enable both DAC channels in cards 1 and 2:

  * ``AmcCard[1:3]: DacEnable: True``

* List slicing behavior:

  * ``AmcCard[1:3]`` -> cards 1 and 2
  * ``AmcCard[:2]`` -> cards 0 and 1
  * ``AmcCard[:]`` -> all cards

* Wildcards:

  * ``AmcCard`` -> all cards
  * ``AmcCard[*]`` -> all cards

Included Command Objects
------------------------

The following :py:class:`pyrogue.LocalCommand` objects are all created when the Root node is created.

* **WriteAll**: Write every variable value to hardware (hidden from the GUI).
* **ReadAll**: Read every variable value from hardware.
* **SaveState**: Save state to file in yaml format.
* **SaveConfig**: Save configuration to file. Data is saved in YAML format.
* **LoadConfig**: Read configuration from file. Data is read in YAML format.
* **RemoteVariableDump**: Save a dump of the remote variable state.
* **RemoteConfigDump**: Save a dump of the remote configuration state.
* **Initialize**: Generate a soft reset to each device in the tree.
* **HardReset**: Generate a hard reset to each device in the tree.
* **CountReset**: Generate a count reset to each device in the tree.
* **ClearLog**: Clear the message log contained in the SystemLog variable.
* **SetYamlConfig**: Set configuration from YAML string.
* **GetYamlConfig**: Get configuration in YAML string.
* **GetYamlState**: Get current state as YAML string.

Included Variable Objects
-------------------------
The following :py:class:`pyrogue.LocalVariable` objects are all created when the Root node is created.

* **RogueVersion**: Rogue version string.
* **RogueDirectory**: Rogue Library Directory.
* **SystemLog**: String containing newline separated system logic entries. Allows remote management interfaces to know when an error has occurred. This string contains a summary of the error while the full trace method is dumped to the console.
* **SystemLogLast**: String containing last system log entry.
* **ForceWrite**: Controls how system level writes are handled. Configuration flag to always write non stale blocks for WriteAll, LoadConfig and setYaml.
* **InitAfterConfig**: Configuration flag to execute initialize after LoadConfig or setYaml.
* **Time**: Current time in seconds since EPOCH UTC.
* **LocalTime**: Local time.
* **PollEn**: Polling worker.

Root Class Documentation
------------------------

.. autoclass:: pyrogue.Root
   :members:
   :member-order: bysource
   :inherited-members:

