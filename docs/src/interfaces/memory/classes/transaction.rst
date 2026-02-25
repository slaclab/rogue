.. _interfaces_memory_transaction:

===========
Transaction
===========

Transaction objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::TransactionPtr

Overview
--------

``Transaction`` is the unit of work that moves through the Rogue memory bus between
``Master`` and ``Slave`` objects. It carries:

- transaction metadata (ID, address, size, type),
- data buffer access (iterators/pointers),
- completion/error state,
- timeout tracking information.

Transactions are not normally constructed by user code. They are created by ``Master``
when a request is issued.

Lifecycle
---------

Typical flow:

1. A master creates and forwards a transaction.
2. One or more slave/hub layers process it.
3. Completion is signaled with ``done()`` or ``error()/errorStr()``.
4. Waiting logic observes completion or timeout.

Each transaction has a unique 32-bit ID used for lookup and correlation.

Locking and Data Access
-----------------------

Transaction payload bytes are accessed via ``begin()``/``end()`` and protected using
``TransactionLock`` (from ``lock()``). Use the lock wrapper whenever reading/writing
 transaction data or completion state from asynchronous code paths.

Timeout and Expiration
----------------------

Timeout is attached to the transaction at creation time. If a transaction is not
completed in time, wait logic marks it with a timeout error. Timer refresh logic can
extend active transactions in multi-stage flows to reduce false expirations on slow links.

Subtransactions
---------------

Hubs and protocol layers can split one parent transaction into multiple child
subtransactions. Parent completion is deferred until all children complete. Child
errors are propagated back to the parent transaction error state.

Why Subtransactions Exist
-------------------------

Subtransactions exist to preserve a simple upstream API while handling downstream
constraints and translation logic.

Common reasons:

- Access-size limits: downstream links may only support smaller transfers than the
  parent request size.
- Address-window translation: a virtual address operation may need to be broken into
  multiple physical operations.
- Protocol decomposition: one logical operation may require multiple wire-level
  transactions.

Using child transactions lets the hub/protocol layer track and retry each piece
independently while still presenting a single completion/error result to the caller.
This keeps master-side code simple and avoids exposing transport-specific fragmentation
details.

Python Integration
------------------

Python-facing APIs expose transaction fields and data access helpers. For Python buffer-
backed transfers, the transaction may hold temporary Python buffer state until completion.

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::Transaction
   :members:
