.. _pyrogue_tree_node_device:

======
Device
======

Device Definition
=================

A :py:class:`pyrogue.Device` is the primary composition unit in a PyRogue tree.
Devices can contain:

* child devices
* variables (local, remote, link)
* commands (local, remote)

Most user-facing hardware abstractions are implemented as ``Device`` subclasses.
At runtime, a Device also participates in memory routing behavior through the
Rogue memory hub stack.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(description='Example device', **kwargs)
           self.add(pr.LocalVariable(name='Mode', mode='RW', value=0))
           self.add(pr.LocalCommand(name='Reset', function=self._reset))

       def _reset(self):
           pass

Key Attributes
--------------

In addition to inherited :ref:`Node <pyrogue_tree_node>` attributes, common
Device-level attributes include:

* ``offset`` / ``address``
* ``memBase``
* ``enable``

The ``enable`` Variable allows tree-level logic to disable a full Device subtree
for hardware access while keeping node metadata available.

Relationship to Hub
-------------------

Conceptually, a Device behaves as a Hub in the memory routing stack:

* Variable/Block transactions are addressed relative to the Device base
* child Devices can inherit base/memory routing from parent Devices
* a child Device can also be attached to an independent memory path when needed

Key Methods
-----------

Commonly used methods:

* :py:meth:`pyrogue.Device.add`
* :py:meth:`pyrogue.Device.addRemoteVariables`
* :py:meth:`pyrogue.Device.hideVariables`
* :py:meth:`pyrogue.Device.initialize`
* :py:meth:`pyrogue.Device.hardReset`
* :py:meth:`pyrogue.Device.countReset`
* :py:meth:`pyrogue.Device.writeBlocks`
* :py:meth:`pyrogue.Device.verifyBlocks`
* :py:meth:`pyrogue.Device.readBlocks`
* :py:meth:`pyrogue.Device.checkBlocks`

.. _pyrogue_tree_node_device_managed_interfaces:

Managed Interfaces: ``addInterface()`` and ``addProtocol()``
-------------------------------------------------------------

Devices can own stream/memory/protocol helper objects that need coordinated
startup/shutdown with the device tree.

Canonical term used in this documentation:
``Managed Interface Lifecycle``.
This refers to the ``_start()`` / ``_stop()`` callback contract for objects
registered through :py:meth:`pyrogue.Device.addInterface`.

Use :py:meth:`pyrogue.Device.addInterface` (or alias
:py:meth:`pyrogue.Device.addProtocol`) to register:

* Rogue memory or stream interface objects
* protocol servers/clients
* any custom object that implements ``_start()`` and/or ``_stop()``

At runtime:

* :py:meth:`pyrogue.Device._start` calls ``_start()`` on each managed object if
  the method exists
* :py:meth:`pyrogue.Device._stop` calls ``_stop()`` on each managed object if
  the method exists
* both then recurse to child devices

This is why top-level interfaces are commonly added at root scope using
``root.addInterface(...)`` (``Root`` is a ``Device`` subclass).

Device Read/Write Operations
----------------------------

Bulk config/read/write operations traverse the tree and issue Block transactions
through Device Block APIs.

Typical write flow:

* update Variable shadow value
* initiate write transaction(s)
* optionally initiate verify transaction(s)
* check completion and publish updates

Typical read flow:

* initiate read transaction(s)
* check completion
* return/publish updated values

Lifecycle Override Points for Subclasses
----------------------------------------

The following methods are intended override points when you need custom
behavior around startup/shutdown or transaction sequencing.

Lifecycle hooks
^^^^^^^^^^^^^^^

* :py:meth:`pyrogue.Device._rootAttached`:
  called during Root startup before ``_finishInit`` and runtime workers
* :py:meth:`pyrogue.Device._start` and :py:meth:`pyrogue.Device._stop`:
  recursive Device lifecycle hooks that drive the
  :ref:`Managed Interface Lifecycle <pyrogue_tree_node_device_managed_interfaces>`

Operational hooks
^^^^^^^^^^^^^^^^^

* :py:meth:`pyrogue.Device.initialize`
* :py:meth:`pyrogue.Device.hardReset`
* :py:meth:`pyrogue.Device.countReset`
* :py:meth:`pyrogue.Device.enableChanged`

Read/write sequencing hooks
^^^^^^^^^^^^^^^^^^^^^^^^^^^

* :py:meth:`pyrogue.Device.writeBlocks`
* :py:meth:`pyrogue.Device.verifyBlocks`
* :py:meth:`pyrogue.Device.readBlocks`
* :py:meth:`pyrogue.Device.checkBlocks`

Override these when default ordering needs pre/post side effects or custom
sequencing.

Implementation Boundary (Python and C++)
----------------------------------------

From a Python API perspective, you use ``pyrogue.Device`` methods such as
``readBlocks`` and ``writeBlocks``.

Under the hood, ``pyrogue.Device`` is built on the Rogue memory interface
Hub/Master/Slave stack. In particular, a Device participates in memory routing
as a Hub, and forwards block transactions toward downstream memory slaves.

Where Hub fits in transaction flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The C++ Hub implementation (``src/rogue/interfaces/memory/Hub.cpp``):

* applies local address offset when forwarding transactions downstream
* can split large transactions into sub-transactions based on downstream
  max-access limits
* allows custom transaction translation by overriding ``_doTransaction`` in
  Python/C++ subclasses

Conceptual transaction path:

* Variable operation -> Block transaction -> Device/Hub routing ->
  downstream slave access -> completion/check -> Variable update notify

For deeper memory-stack behavior, see:

* :doc:`/pyrogue_tree/core/blocks`
* :doc:`/memory_interface/hub`
* :doc:`/memory_interface/slave`
* :doc:`/api/cpp/interfaces/memory/index`

Custom Read/Write Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a Device needs sequencing around default Block operations, override:

* :py:meth:`pyrogue.Device.writeBlocks`
* :py:meth:`pyrogue.Device.verifyBlocks`
* :py:meth:`pyrogue.Device.readBlocks`
* :py:meth:`pyrogue.Device.checkBlocks`

.. code-block:: python

   class SequencedDevice(pyrogue.Device):
       def writeBlocks(self, *, force=False, recurse=True, variable=None, checkEach=False, index=-1):
           # Pre-transaction behavior
           super().writeBlocks(
               force=force,
               recurse=recurse,
               variable=variable,
               checkEach=checkEach,
               index=index,
           )
           # Post-transaction behavior


Device Command Decorators
-------------------------

Device supports decorators that create :py:class:`pyrogue.LocalCommand` nodes.
You can use decorators on local functions created in ``__init__``.

.. code-block:: python

   @pyrogue.command(name='ReadConfig', value='', description='Load config file')
   def _readConfig(self, arg):
       self.root.loadYaml(name=arg, writeEach=False, modes=['RW', 'WO'])

Special Device Subclasses
=========================

There are several specialized device classes available:

.. toctree::
   :maxdepth: 1
   :caption: Special Device Subtypes:

   /pyrogue_tree/builtin_devices/run_control
   /pyrogue_tree/builtin_devices/data_writer
   /pyrogue_tree/builtin_devices/data_receiver
   /pyrogue_tree/builtin_devices/prbsrx
   /pyrogue_tree/builtin_devices/prbstx
   /pyrogue_tree/builtin_devices/prbspair
   /pyrogue_tree/builtin_devices/stream_reader
   /pyrogue_tree/builtin_devices/stream_writer
   /pyrogue_tree/builtin_devices/process

Device API Reference
==========================

See :doc:`/api/python/device` for generated API details.
