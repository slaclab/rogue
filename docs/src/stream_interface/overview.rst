.. _stream_interface_overview:

=========================
Stream Interface Overview
=========================

The stream interface provides a mechanism for moving bulk data between modules
within Rogue.

A stream interface consists of:

- a ``Master`` as the source of a Rogue frame
- a ``Slave`` as the destination of the frame
- a ``Frame`` container that carries a series of payload buffers

Data flow lifecycle
===================

1. A ``Master`` allocates or forwards a ``Frame``.
2. Processing stages may inspect, transform, or annotate payload data.
3. A ``Slave`` consumes frames and applies backpressure as needed.
4. Ownership and lifetime are managed so high-rate paths stay in C++.

Design guidance
===============

- Keep pipeline stages focused and composable.
- Use explicit buffering points where producer/consumer rates differ.
- Place debug and instrumentation modules near suspected bottlenecks.
- Prefer architectural docs for flow design; use API docs for contracts.

This page is now the canonical conceptual home for stream architecture
guidance. Legacy narrative remains available at :doc:`/stream_interface/legacy_stream/index`.

Main usage and examples:

- :doc:`/stream_interface/legacy_stream/index`

Core API reference:

- :doc:`/api/cpp/interfaces/stream/frame`
- :doc:`/api/cpp/interfaces/stream/master`
- :doc:`/api/cpp/interfaces/stream/slave`
