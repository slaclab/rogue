.. _pyrogue_tree_node_root:

====
Root
====

The :py:class:`~pyrogue.Root` class is the top-level Node in a PyRogue tree.
It owns the runtime lifecycle of the full application, coordinates whole-tree
read and write workflows, manages background services such as polling and
update propagation, and provides the common entry points used by GUIs, remote
clients, and YAML-based configuration flows.

``Root`` also inherits from :py:class:`~pyrogue.Device`. That is important
because the top of the tree participates in the same child-Device hierarchy,
managed-interface lifecycle, and block-traversal behavior as the rest of the
tree. In practice, that is why a ``Root`` can own interfaces, recurse through
child Devices during startup and shutdown, and serve as the top-level entry
point for bulk read and write operations.

Most applications define one ``Root`` subclass and then build the rest of the
tree underneath it. In practice, that means ``Root`` is where you decide:

* How the tree is exposed to remote tools.
* Which memory or transport interfaces the design uses.
* How startup and shutdown should happen.
* Which top-level system actions and configuration workflows are available.

What Root Usually Owns
======================

``Root`` is not just a container. It is the object that turns a static tree
definition into a live system.

A typical ``Root`` subclass does four things:

1. Creates the hardware-facing interface path used for register access.
2. Adds top-level ``Device`` instances to the tree and connects them to the hardware interface.
3. Optionally exposes the running tree to remote tools such as PyDM or client
   scripts.

For most DAQ-style applications, the first step means opening the connection to
the hardware itself or to a simulation of that hardware. In practice that often
means opening a device driver,
:doc:`/built_in_modules/hardware/dma/index`,
:doc:`/memory_interface/tcp_bridge`, or another transport path through a
Rogue-provided wrapper.

The key outcome of that step is usually one or more Rogue memory-interface
objects. Those objects are the link between the hardware connection and the
PyRogue tree: they are passed as ``memBase`` to ``Device`` instances so that
``RemoteVariable`` and other hardware-backed Nodes have a path for register
transactions.

.. code-block:: python

   import pyrogue as pr
   import rogue
   import pyrogue.interfaces
   import axipcie

   class EvalBoard(pr.Root):
       def __init__(self, dev='/dev/datadev_0', **kwargs):
           super().__init__(name='EvalBoard', description='Evaluation board root', **kwargs)

           # Create the memory-mapped hardware interface.
           self.memMap = rogue.hardware.axi.AxiMemMap(dev)

           # Register it so tree transactions can route through Root.
           self.addInterface(self.memMap)

           # Expose the tree to remote tools.
           self.zmqServer = pyrogue.interfaces.ZmqServer(
               root=self,
               addr='127.0.0.1',
               port=0,
           )
           self.addInterface(self.zmqServer)

           # Add the application-specific tree beneath Root.
           self.add(axipcie.AxiPcieCore(
               offset=0x00000000,
               memBase=self.memMap,
               expand=True,
           ))

That composition pattern is the normal starting point for PyRogue systems:
``Root`` owns lifecycle and top-level interfaces, while ``Device`` instances
carry the hardware and application structure below it.

Lifecycle And Startup
=====================

The main lifecycle entry points on ``Root`` are
:py:meth:`~pyrogue.Root.start` and :py:meth:`~pyrogue.Root.stop`.

``Root.start()`` does more than start background threads. It performs the full
bring-up sequence that attaches the tree, finalizes Node initialization, starts
managed interfaces, runs optional initial read or write operations, and then
enables polling.

Startup Sequence
----------------

When :py:meth:`~pyrogue.Root.start` runs, the major stages are:

#. Attach the full tree with ``_rootAttached()``.
#. Run ``_finishInit()`` across the full hierarchy.
#. Validate the collected memory ``Block`` layout.
#. Apply timeout settings.
#. Start background update and heartbeat services.
#. Call :py:meth:`~pyrogue.Device._start` recursively from the root.
#. Optionally perform initial bulk read and write flows.
#. Start :py:class:`~pyrogue.PollQueue` and apply ``PollEn`` state.

The important practical point is that a PyRogue tree is not fully live until
that sequence has completed. Before startup, the structure exists, but runtime
behaviors such as polling, managed-interface startup, and hardware-backed block
access should be treated as not yet active.

Shutdown Sequence
-----------------

When :py:meth:`~pyrogue.Root.stop` runs, it:

#. Marks the Root as no longer running.
#. Stops the update worker thread.
#. Stops :py:class:`~pyrogue.PollQueue`.
#. Calls :py:meth:`~pyrogue.Device._stop` recursively from the root.

That shutdown path is why device-owned runtime resources should normally be
started in ``_start()`` and stopped in ``_stop()`` rather than being managed ad
hoc elsewhere.

Tree Attachment And Lookup
==========================

During startup, ``Root`` is also responsible for attaching parent, root, and
path context to the entire tree. That happens through ``_rootAttached()``.

At a high level:

* ``Root`` sets its own parent and root references to itself.
* ``Root`` establishes its full path from its name.
* Child Nodes are recursively attached with resolved parent/root/path context.
* ``Device``-level attach logic builds the ``Block`` layout used by hardware
  access paths.

Once the tree is attached, :py:meth:`~pyrogue.Root.getNode` can resolve dotted
paths such as ``EvalBoard.AxiVersion.ScratchPad``. This is one of the key ways
tooling and remote interfaces address Nodes in a running system.

Interfaces And Remote Access
============================

``Root`` is also where remote access usually enters the system. The most common
pattern is to add a :py:class:`~pyrogue.interfaces.ZmqServer` so that PyDM,
client scripts, and other tools can connect to the same live tree.

Common pattern in ``Root.__init__``:

* Create ``pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=0)``
* Register it with :py:meth:`~pyrogue.Root.addInterface`

Practical notes:

* ``port=0`` auto-selects the first available base port starting at ``9099``.
* Binding to ``127.0.0.1`` keeps the interface local to the host.
* Other deployments can bind to a non-local address as needed.

For the broader client-side workflows built on top of that interface, see:

* :doc:`/pyrogue_tree/client_interfaces/index`
* :doc:`/pyrogue_tree/client_interfaces/zmq_server`
* :doc:`/pyrogue_tree/client_interfaces/simple`
* :doc:`/pyrogue_tree/client_interfaces/virtual`

Polling And Critical Sections
=============================

``Root`` owns :py:class:`~pyrogue.PollQueue`, which schedules periodic reads
for polled Variables. In most applications, you do not instantiate or manage
the poll queue directly; instead, you control it through ``Root`` and Variable
settings such as ``PollEn`` and ``pollInterval``.

Use :py:meth:`~pyrogue.Root.pollBlock` when a short sequence should not race
with background poll reads.

.. code-block:: python

   with root.pollBlock():
       root.MyDevice.SomeControl.set(1)
       root.MyDevice.OtherControl.set(0)

For the detailed scheduling and behavior model, see
:doc:`/pyrogue_tree/core/poll_queue`.

YAML Configuration And Bulk Operations
======================================

``Root`` provides the main tree-level YAML and bulk I/O entry points:

* :py:meth:`~pyrogue.Root.saveYaml`
* :py:meth:`~pyrogue.Root.loadYaml`
* :py:meth:`~pyrogue.Root.setYaml`
* :py:meth:`~pyrogue.Node.getYaml`

These methods back the built-in configuration and state commands exposed on the
Root itself. They are the main mechanism for saving baselines, restoring known
configurations, and applying configuration changes across the whole tree.

For YAML matching, file formats, and array slicing, see
:doc:`/pyrogue_tree/core/yaml_configuration`.

For the bulk transaction model used when those staged values are committed
through the tree, see :doc:`/pyrogue_tree/core/block_operations`.

Built-In Root Commands And Variables
====================================

Every ``Root`` instance includes a set of built-in control Nodes that support
system-wide workflows.

Built-in Commands
-----------------

The following :py:class:`~pyrogue.LocalCommand` objects are created with the
Root:

* ``WriteAll``: Write every Variable value to hardware.
* ``ReadAll``: Read every Variable value from hardware.
* ``SaveState``: Save current state to YAML.
* ``SaveConfig``: Save configuration to YAML.
* ``LoadConfig``: Load configuration from YAML.
* ``RemoteVariableDump``: Save a dump of remote Variable state.
* ``RemoteConfigDump``: Save a dump of remote configuration state.
* ``Initialize``: Invoke initialize behavior across the tree.
* ``HardReset``: Invoke hard-reset behavior across the tree.
* ``CountReset``: Invoke count-reset behavior across the tree.
* ``ClearLog``: Clear the Root system log.
* ``SetYamlConfig``: Apply configuration from YAML text.
* ``GetYamlConfig``: Return configuration as YAML text.
* ``GetYamlState``: Return state as YAML text.

Built-in Variables
------------------

The following :py:class:`~pyrogue.LocalVariable` objects are also created with
the Root:

* ``RogueVersion``: Rogue version string.
* ``RogueDirectory``: Rogue library directory.
* ``SystemLog``: System log contents for remote tools.
* ``SystemLogLast``: Most recent system log entry.
* ``ForceWrite``: Controls whether non-stale Blocks are forced during bulk
  config writes.
* ``InitAfterConfig``: Controls whether ``initialize()`` runs after config
  application.
* ``Time``: Current UTC time in seconds since epoch.
* ``LocalTime``: Current local time.
* ``PollEn``: Global polling enable.

Built-In Groups
===============

Root-level configuration and state workflows use group filtering to include or
exclude Nodes from bulk operations.

Common built-in groups include:

* ``NoConfig``: Excluded from configuration save and load operations.
* ``NoState``: Excluded from state snapshot and export operations.
* ``Hidden``: Hidden from normal GUI views unless explicitly included.

For the full group-filtering model, see :doc:`/pyrogue_tree/core/groups`.

What To Explore Next
====================

* Device composition beneath Root: :doc:`/pyrogue_tree/core/device`
* Variable behavior and access patterns: :doc:`/pyrogue_tree/core/variable`
* Poll scheduling behavior: :doc:`/pyrogue_tree/core/poll_queue`
* YAML configuration workflows: :doc:`/pyrogue_tree/core/yaml_configuration`
* Remote access patterns: :doc:`/pyrogue_tree/client_interfaces/index`

API Reference
=============

See :doc:`/api/python/pyrogue/root` for generated API details.
