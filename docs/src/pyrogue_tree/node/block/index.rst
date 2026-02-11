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

.. autoclass:: pyrogue.LocalBlock
   :members:
   :member-order: bysource
