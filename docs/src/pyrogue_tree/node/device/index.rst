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
At runtime, a device also participates in memory routing behavior through the
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
device-level attributes include:

* ``offset`` / ``address``
* ``memBase``
* ``enable``

The ``enable`` variable allows tree-level logic to disable a full device subtree
for hardware access while keeping node metadata available.

Relationship to Hub
-------------------

Conceptually, a device behaves as a hub in the memory routing stack:

* variable/block transactions are addressed relative to the device base
* child devices can inherit base/memory routing from parent devices
* a child device can also be attached to an independent memory path when needed

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

Device Read/Write Operations
----------------------------

Bulk config/read/write operations traverse the tree and issue block transactions
through device block APIs.

Typical write flow:

* update variable shadow value
* enqueue write transaction
* optionally enqueue verify transaction
* check completion and publish updates

Typical read flow:

* enqueue read transaction
* check completion
* return/publish updated values

Implementation Boundary (Python and C++)
----------------------------------------

From a Python API perspective, you use ``pyrogue.Device`` methods such as
``readBlocks`` and ``writeBlocks``.

Under the hood, ``pyrogue.Device`` is built on the Rogue memory interface
hub/master/slave stack. In particular, a device participates in memory routing
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

* variable operation -> block transaction -> device/hub routing ->
  downstream slave access -> completion/check -> variable update notify

For deeper memory-stack behavior, see:

* :ref:`interfaces_memory_blocks`
* :ref:`interfaces_memory_hub`
* :ref:`interfaces_memory_hub_ex`
* :ref:`interfaces_memory_classes`

Custom Read/Write Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a device needs sequencing around default block operations, override:

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

   special_devices/run_control
   special_devices/data_writer
   special_devices/data_receiver
   special_devices/prbsrx
   special_devices/prbstx
   special_devices/prbspair
   special_devices/stream_reader
   special_devices/stream_writer
   special_devices/process

Device Class Documentation
==========================

.. autoclass:: pyrogue.Device
   :members:
   :member-order: bysource
   :inherited-members:
