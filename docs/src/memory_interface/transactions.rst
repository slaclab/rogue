.. _memory_interface_transactions:

=================================
Memory Transactions and Lifecycle
=================================

Overview
========

``Transaction`` is the unit of work that moves through the Rogue memory bus
between ``Master`` and ``Slave`` objects. It carries metadata (ID, address,
size, and type), payload access, completion/error state, and timeout tracking.

Transactions are typically created by ``Master`` when a request is issued.

Lifecycle
=========

Typical flow:

1. A master creates and forwards a transaction.
2. One or more slave or hub layers process it.
3. Completion is signaled with ``done()`` or ``error()/errorStr()``.
4. Wait logic observes completion or timeout.

Each transaction has a unique 32-bit ID used for lookup and correlation.

Locking and Data Access
=======================

Transaction payload bytes are accessed via ``begin()``/``end()`` and protected
using ``TransactionLock`` from ``lock()``.

Use the lock wrapper when reading or writing transaction payload/state from
asynchronous paths.

Timeout and Expiration
======================

Timeout is attached at creation. If a transaction does not complete in time,
wait logic marks it as a timeout error.

Timer refresh logic can extend active transactions in multi-stage flows to
reduce false expirations on slower links.

Subtransactions
===============

Hubs and protocol layers may split one parent transaction into multiple child
transactions. Parent completion is deferred until all children complete.

Child errors propagate to the parent transaction error state.

Why Subtransactions Exist
=========================

Subtransactions preserve a simple upstream API while handling downstream
constraints:

- Access-size limits on downstream links
- Address window translation
- Protocol decomposition into wire-level operations

This keeps master-side code simple and hides transport fragmentation details.

Python Integration
==================

Python-facing APIs expose transaction fields and data access helpers.
For Python buffer-backed transfers, transactions may hold temporary buffer
state until completion.

Related API reference:

- :doc:`/api/cpp/interfaces/memory/transaction`
- :doc:`/api/cpp/interfaces/memory/transactionLock`
- :doc:`/api/cpp/interfaces/memory/master`
- :doc:`/api/cpp/interfaces/memory/hub`
