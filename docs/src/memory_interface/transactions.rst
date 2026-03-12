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

Lifecycle
=========

The normal lifecycle looks like this:

1. A ``Master`` creates and forwards a ``Transaction``.
2. One or more ``Hub`` or ``Slave`` layers process it.
3. Completion is reported with ``done()`` or with an error call such as
   ``error()``.
4. Waiting code observes completion, failure, or timeout.

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

Longer multi-stage flows can refresh timer state so an active but slow
``Transaction`` does not expire prematurely. That matters most for deeper hub
graphs, protocol bridges, and slower transport links.

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
