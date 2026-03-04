.. _memory_interface_overview:

=========================
Memory Interface Overview
=========================

The Rogue memory interface provides a mechanism for interfacing with hardware
register space, including reading and writing memory spaces while keeping a
local mirror of current register sets.

Address spaces can be created organically by linking memory masters to memory
hubs, with eventual connection to a memory slave that serves as the hardware
interface.

Each memory access is associated with a transaction object used to describe and
track in-progress accesses. Transactions are forwarded through memory-bus
layers with address adjustment based on hub/device connections. A hub may also
split a single transaction into multiple downstream transactions when needed
for complex memory spaces.

Most users interact through PyRogue tree abstractions rather than direct
low-level memory APIs.

This page is now the canonical conceptual home for memory architecture
guidance. Legacy narrative remains available at :doc:`/interfaces/memory/index`.

Start with:

- :doc:`/interfaces/memory/index`
- :doc:`/memory_interface/transactions`
