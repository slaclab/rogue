.. _memory_interface_transactions:

=================================
Memory Transactions and Lifecycle
=================================

``Transaction`` is the unit of work that moves through the Rogue memory bus.
Every read, write, posted write, verify, routed access, or TCP-forwarded memory
operation is represented as a ``Transaction``.

A ``Transaction`` carries both the request description and the state needed to
track it while it is in flight. That includes the address, type, transfer size,
payload access, completion state, error state, and timeout handling.

What A ``Transaction`` Carries
==============================

A ``Transaction`` typically carries:

- A unique transaction ID
- The target address
- The access type
- The transfer size
- Payload access for read or write data
- Completion and error state
- Timeout and expiration information

Most users do not construct ``Transaction`` objects directly. They are usually
created by a ``Master`` when a request is issued.

Access Types
============

The most important ``Transaction`` types are:

- ``Read`` requests data from the downstream target.
- ``Write`` sends data through the normal write path.
- ``Post`` sends data as a posted write.
- ``Verify`` checks that downstream state matches the expected value.

For many custom ``Slave`` or ``Hub`` implementations, ``Write`` and ``Post``
look almost identical at the transport boundary: both carry outbound write
data. The important distinction is semantic. A posted write is a distinct
transaction type in the Rogue memory model, so downstream code can choose to
handle it differently when the protocol or hardware behavior requires that.

In practice, some implementations intentionally treat ``Write`` and ``Post``
the same, while others use ``Post`` for command-like or non-readback-oriented
operations.

Lifecycle
=========

The normal lifecycle looks like this:

1. A ``Master`` creates and forwards a ``Transaction``.
2. One or more ``Hub`` or ``Slave`` layers process it.
3. Completion is reported with ``done()`` or with an error call such as
   ``error()``.
4. Waiting code observes completion, failure, or timeout.

Posted writes are not a separate lifecycle mechanism. They still move through
the same ``Transaction`` machinery as reads, writes, and verifies: a
``Master`` creates the ``Transaction``, downstream components process it, and
completion or error is reported in the normal way.

The difference is the access type. A downstream ``Slave`` or ``Hub`` can see
that the request is ``Post`` instead of ``Write`` and choose different
behavior if the protocol or hardware requires it. Some implementations treat
``Post`` exactly like ``Write``. Others use it for write paths that should not
wait for a normal downstream response, or for other command-oriented policies.

Each ``Transaction`` has a unique 32-bit ID that can be used for lookup,
correlation, or asynchronous completion handling.

Locking And Data Access
=======================

``Transaction`` payload bytes are accessed through pointer and iterator-style
interfaces such as ``begin()`` and are protected by ``TransactionLock`` from
``lock()``.

Whenever asynchronous code reads or writes ``Transaction`` payload or state, it
should do so under the ``Transaction`` lock. This is especially important in
custom ``Slave`` or ``Hub`` implementations that recover a stored
``Transaction`` later from a callback or worker thread.

Timeout And Expiration
======================

Timeout is attached when the ``Transaction`` is created. If the work does not
complete in time, waiting logic marks the ``Transaction`` as a timeout error.

Timer refresh logic can extend active transactions in multi-stage flows to
reduce false expirations on slower links.
Longer multi-stage flows can refresh timer state so an active but slow
``Transaction`` does not expire prematurely. That matters most for deeper hub
graphs, protocol bridges, and slower transport links.

Logging
=======

The transaction runtime uses a Rogue C++ logger:

- Logger name: ``pyrogue.memory.Transaction``
- Unified Logging API:
  ``logging.getLogger('pyrogue.memory.Transaction').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.memory.Transaction', rogue.Logging.Debug)``

This logger is created in quiet mode and is mainly an internal runtime aid for
timeout/correlation behavior rather than a primary user-facing debug surface.

In practice, transaction debugging is usually more effective through the
surrounding module loggers:

- ``pyrogue.memory.Master`` for request issue paths
- ``pyrogue.memory.Hub`` for routing/splitting paths
- ``pyrogue.memory.block.*`` for Variable/Block transaction flow
- Protocol-specific loggers such as ``pyrogue.SrpV3``

Subtransactions
===============

One important feature of the memory interface is that a single parent
``Transaction`` may be split into multiple child transactions. ``Hub`` and
protocol layers use this when one upstream request must be decomposed before it
can be serviced downstream.

Parent completion is deferred until all child work completes, and child errors
propagate back to the parent error state.

Why Subtransactions Exist
=========================

Subtransactions let upstream code stay simple while downstream details remain
hidden. Common reasons for splitting include:

- Access-size limits on a downstream link
- Address-window translation
- Protocol decomposition into several wire-level operations

This keeps the upstream ``Master`` API straightforward even when the transport
or bus structure underneath is more complicated.

Python Integration
==================

Python-facing APIs expose ``Transaction`` fields and payload access helpers. For
buffer-backed Python transfers, a ``Transaction`` may also hold temporary buffer
state until the operation completes.

In most Python code, this shows up indirectly through ``Master``, ``Slave``,
and ``Hub`` implementations rather than through direct user construction of a
``Transaction``.

What To Explore Next
====================

- Custom ``Master`` patterns: :doc:`/memory_interface/master`
- Custom ``Slave`` patterns: :doc:`/memory_interface/slave`
- ``Hub`` translation patterns: :doc:`/memory_interface/hub`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/memory/transaction`
  - :doc:`/api/python/rogue/interfaces/memory/master`
  - :doc:`/api/python/rogue/interfaces/memory/hub`

- C++:

  - :doc:`/api/cpp/interfaces/memory/transaction`
  - :doc:`/api/cpp/interfaces/memory/transactionLock`
  - :doc:`/api/cpp/interfaces/memory/master`
  - :doc:`/api/cpp/interfaces/memory/hub`
