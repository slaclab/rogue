.. _pyrogue_tree_block_operations:

=======================
Device Block Operations
=======================

This page describes the ``Device``-level methods that traverse a tree and
initiate or check ``Block`` transactions:

* :py:meth:`~pyrogue.Device.writeBlocks`
* :py:meth:`~pyrogue.Device.verifyBlocks`
* :py:meth:`~pyrogue.Device.readBlocks`
* :py:meth:`~pyrogue.Device.checkBlocks`

These methods are the bridge between the higher-level tree model and the lower-
level ``Block`` transaction layer. They are also the normal extension points
when a Device needs custom hardware sequencing.

What These Methods Do
=====================

At a high level:

* ``writeBlocks`` initiates write transactions.
* ``verifyBlocks`` initiates verify transactions.
* ``readBlocks`` initiates read transactions.
* ``checkBlocks`` waits for previously initiated transactions to complete.

This split is intentional. In PyRogue, initiating an operation and waiting for
it to complete are separate steps. That allows many transactions to be issued
first and then checked afterward.

Composed helpers such as ``writeAndVerifyBlocks`` and ``readAndCheckBlocks``
are built from these same methods.

Full-Device Traversal Order
===========================

For the full-Device case, traversal happens in this order:

1. Issue Transactions for the ``Block`` objects attached directly to the current ``Device``.
2. Recurse into child Devices if ``recurse=True``.

So when a Device has both its own Blocks and child Devices, the current
Device's Blocks are handled first. Child Devices are processed afterward.

Ordering Within A Device
========================

The ordering inside each Device is also defined.

Child Device Order
------------------

Child Devices are visited in the order they were added to the parent. ``Node``
stores children in an ``OrderedDict``, and ``Device`` recurses through
``self.devices.values()``.

Automatically Built Remote Blocks
---------------------------------

Automatically built hardware-backed Blocks are created from Variables sorted by
``(offset, varBytes)``. In practice, that means auto-built Blocks are normally
issued in address-oriented order.

Local Blocks
------------

``LocalVariable`` Blocks are appended as the Device walks its child Nodes, so
they follow Node insertion order rather than address sorting.

Single-Variable Operations
==========================

The same methods can also target one specific Variable by passing
``variable=...``.

That path skips full subtree traversal and instead operates on the Block
associated with that Variable. This is how many per-Variable hardware-backed
``get`` and ``set`` operations reuse the same Device block methods without
turning into full-tree operations.

Where These Methods Are Used
============================

These methods are often called indirectly rather than manually.

Common examples:

* Hardware-backed Variable reads and writes use the Device block methods under
  the hood.
* Root-level YAML apply and bulk read/write flows recurse through these
  methods.
* Custom Devices override these methods when hardware needs extra sequencing.

Custom Sequencing
=================

Override these methods when the hardware access sequence must do more than the
default Device-first, then-child-Devices traversal.

Common examples:

* Page or bank selection registers that must be written around access.
* Commit or apply strobes that must follow configuration writes.
* Required pre- or post-register transactions around a bulk operation.
* Custom ordering across child Devices.

Typical override pattern:

.. code-block:: python

   class SequencedDevice(pyrogue.Device):
       def writeBlocks(self, *, force=False, recurse=True, variable=None, checkEach=False, index=-1):
           # Pre-transaction behavior.
           super().writeBlocks(
               force=force,
               recurse=recurse,
               variable=variable,
               checkEach=checkEach,
               index=index,
           )
           # Post-transaction behavior.

What To Explore Next
====================

* What Blocks are and how Variables map into them: :doc:`/pyrogue_tree/core/block`
* Device structure and lifecycle hooks: :doc:`/pyrogue_tree/core/device`
* Variable behavior and hardware-backed access paths: :doc:`/pyrogue_tree/core/variable`
