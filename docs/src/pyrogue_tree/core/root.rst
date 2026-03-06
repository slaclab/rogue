.. _pyrogue_tree_node_root:

====
Root
====

The :py:class:`pyrogue.Root` class is the top-level Node in a PyRogue tree.
It owns the application lifecycle, coordinates bulk read/write operations,
manages background workers (poll and update), and provides APIs for YAML
save/load and external listeners.

For polling internals and usage patterns, see
:ref:`pyrogue_tree_root_poll_queue`.

Most user applications define a subclass of ``pyrogue.Root`` and add Devices
inside ``__init__``.

In practice, ``Root`` is also where hardware connections are usually created and
bound into the tree. A typical pattern is:

* create a memory interface (for example AXI PCIe, TCP simulation, etc.)
* register it with :py:meth:`pyrogue.Root.addInterface`
* pass that interface as ``memBase`` when adding top-level Devices
* optionally add management/control interfaces (such as ZMQ) to the same Root

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

Lifecycle and Startup Sequence
------------------------------

``Root`` controls startup and shutdown for the full tree.
The two calls that matter operationally are :py:meth:`pyrogue.Root.start` and
:py:meth:`pyrogue.Root.stop`.

``Root.start()`` sequence
^^^^^^^^^^^^^^^^^^^^^^^^^

When :py:meth:`pyrogue.Root.start` runs, it performs bring-up in this order:

#. Verifies the Root is not already running (raises if it is).
#. Calls ``Root._rootAttached()``.

   * Root sets its own parent/root/path fields.
   * Root calls ``_rootAttached(parent, root)`` on all child Nodes.
   * Each Device ``_rootAttached`` call recursively attaches children, builds
     Device Blocks, and applies ``_defaults`` overrides.
   * Root then builds its own Blocks and runs ``_finishInit()`` on Root-local
     Variables that depend on built Blocks.

#. Calls ``Root._finishInit()`` recursively on the full tree.
#. Collects all memory Blocks, sorts by ``(slaveId, address, size)``, and
   checks for overlapping address ranges per slave ID.
#. Applies timeout settings via ``_setTimeout`` when Root timeout is not the
   default value.
#. Sets ``running=True`` and starts the update worker thread.
#. Starts heartbeat thread if enabled.
#. Calls :py:meth:`pyrogue.Device._start` on Root.

   * For each Device, managed interfaces/protocols receive ``_start()`` first.
   * Then ``_start()`` recurses into child Devices.

#. Runs optional startup read (``_initRead``) via ``Root._read()``.
#. Runs optional startup write/verify/check (``_initWrite``) via ``Root._write()``.
#. Starts :py:class:`pyrogue.PollQueue` and then applies ``PollEn`` state.

After this sequence, the tree is live for client access, polling, and normal
read/write workflows.

``Root.stop()`` sequence
^^^^^^^^^^^^^^^^^^^^^^^^

When :py:meth:`pyrogue.Root.stop` runs:

#. Sets ``running=False``.
#. Pushes stop sentinel to the update queue and joins the update worker thread.
#. Stops :py:class:`pyrogue.PollQueue`.
#. Calls :py:meth:`pyrogue.Device._stop` on Root.

   * For each Device, managed interfaces/protocols receive ``_stop()`` first.
   * Then ``_stop()`` recurses into child Devices.

``getNode`` path lookup
^^^^^^^^^^^^^^^^^^^^^^^

:py:meth:`pyrogue.Root.getNode` resolves dotted paths such as
``EvalBoard.AxiVersion.ScratchPad`` and is commonly used by tooling and
client-facing helpers.

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

For broader client/interface selection and deployment patterns, see
:doc:`/pyrogue_tree/client_interfaces/index`,
:doc:`/pyrogue_tree/client_interfaces/zmq_server`,
:doc:`/pyrogue_tree/client_interfaces/simple`, and
:doc:`/pyrogue_tree/client_interfaces/virtual`.

Built-in Groups
---------------

PyRogue Root-level configuration/state Commands use group filtering to include
or exclude Variables and Commands from bulk operations.

Common built-in group names:

* ``NoConfig``: excluded from configuration save/load operations.
* ``NoState``: excluded from state snapshot/export operations.
* ``Hidden``: hidden from normal GUI views unless explicitly included.

See :ref:`pyrogue_tree_node_groups` for full built-in group behavior and filtering semantics.


YAML Configuration and Bulk Operations
--------------------------------------

Root YAML config/state workflows and array-matching rules are documented in:

- :doc:`/pyrogue_tree/core/yaml_configuration`

That page also covers bulk initiate/check behavior and related Root settings
(``ForceWrite``, ``InitAfterConfig``).

Included Command Objects
------------------------

The following :py:class:`pyrogue.LocalCommand` objects are all created when the Root Node is created.

* **WriteAll**: Write every Variable value to hardware (hidden from the GUI).
* **ReadAll**: Read every Variable value from hardware.
* **SaveState**: Save state to file in yaml format.
* **SaveConfig**: Save configuration to file. Data is saved in YAML format.
* **LoadConfig**: Read configuration from file. Data is read in YAML format.
* **RemoteVariableDump**: Save a dump of the remote Variable state.
* **RemoteConfigDump**: Save a dump of the remote configuration state.
* **Initialize**: Generate a soft reset to each Device in the tree.
* **HardReset**: Generate a hard reset to each Device in the tree.
* **CountReset**: Generate a count reset to each Device in the tree.
* **ClearLog**: Clear the message log contained in the SystemLog Variable.
* **SetYamlConfig**: Set configuration from YAML string.
* **GetYamlConfig**: Get configuration in YAML string.
* **GetYamlState**: Get current state as YAML string.

Included Variable Objects
-------------------------
The following :py:class:`pyrogue.LocalVariable` objects are created when the
Root Node is created.

* **RogueVersion**: Rogue version string.
* **RogueDirectory**: Rogue Library Directory.
* **SystemLog**: String containing newline-separated system log entries. Allows remote client interfaces to know when an error has occurred. This string contains a summary of the error while the full traceback is dumped to the console.
* **SystemLogLast**: String containing last system log entry.
* **ForceWrite**: Controls how system level writes are handled. Configuration flag to always write non stale Blocks for WriteAll, LoadConfig and setYaml.
* **InitAfterConfig**: Configuration flag to execute initialize after LoadConfig or setYaml.
* **Time**: Current time in seconds since EPOCH UTC.
* **LocalTime**: Local time.
* **PollEn**: Polling worker.

Root API Reference
------------------------

See :doc:`/api/python/root` for generated API details.
