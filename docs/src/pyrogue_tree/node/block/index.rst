.. _pyrogue_tree_node_block:

=====
Block
=====

Blocks are the transaction units used by PyRogue for memory I/O.

At runtime, variables (especially :py:class:`pyrogue.RemoteVariable`) are packed
into one or more blocks. Read/write/verify operations are issued at block level,
then values are mapped back to individual variables.

How Variables Use Blocks
========================

For :py:class:`pyrogue.RemoteVariable`:

* each variable defines offset/bit mapping metadata
* during device attach/build, device logic groups compatible remote variables
  into blocks
* each variable gets ``_block`` pointing to the block that services it
* transaction methods on Device/Root call block transactions, not per-variable
  raw bus operations

For :py:class:`pyrogue.LocalVariable`:

* each variable uses a local software block (:py:class:`pyrogue.LocalBlock`)
  for in-memory set/get behavior

Access Path (RemoteVariable)
============================

Typical read/write path:

* user/API calls ``set`` or ``get`` on a variable
* Device/Root APIs enqueue block transactions
* block reads/writes memory through the device's memory interface
* completion/check updates variable state and notifications

In bulk operations, many variables can share one block transaction, improving
access efficiency versus isolated per-variable transfers.

Block Helper API
================

PyRogue provides helper functions around block transaction flow:

* :py:func:`pyrogue.startTransaction`
* :py:func:`pyrogue.checkTransaction`
* :py:func:`pyrogue.writeBlocks`
* :py:func:`pyrogue.verifyBlocks`
* :py:func:`pyrogue.readBlocks`
* :py:func:`pyrogue.checkBlocks`
* :py:func:`pyrogue.writeAndVerifyBlocks`
* :py:func:`pyrogue.readAndCheckBlocks`

These helpers are used by device-level methods and are the preferred extension
points for custom block sequencing.

Implementation Boundary (Python and C++)
========================================

The block API you call from PyRogue maps to the ``rogue.interfaces.memory``
runtime layer.

In practice:

* Python code invokes methods on ``pyrogue.Device`` / ``pyrogue.RemoteVariable``
* these route into block/variable objects exposed by
  ``rogue.interfaces.memory``
* the underlying C++ block/variable code handles transaction staging,
  read/write/verify behavior, stale tracking, packing/unpacking, and update
  notification triggers

Hub interaction
===============

Blocks are transaction sources; Hubs are transaction routers.

During a transaction, Hub logic:

* offsets addresses by local hub/device base
* forwards transaction to downstream memory slave
* splits transaction into sub-transactions when request size exceeds downstream
  max-access capability

This is why a variable-to-block transaction can still work cleanly across
multi-level device trees with address translation.

For deeper internals and extension patterns, see:

* :ref:`interfaces_memory_blocks`
* :ref:`interfaces_memory_hub`
* :ref:`interfaces_memory_hub_ex`
* :ref:`interfaces_memory_classes`

Example
=======

.. code-block:: python

   # Bulk read all blocks attached to a device
   myDevice.readBlocks(recurse=True)
   myDevice.checkBlocks(recurse=True)

   # Variable-specific transaction (targets variable._block)
   myDevice.writeBlocks(variable=myDevice.MyReg, checkEach=True)

Block/LocalBlock Class Documentation
====================================

See :doc:`/api/python/localblock` for generated API details.
