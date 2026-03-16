.. _stream_interface_built_in_modules:

=======================
Built-in Stream Modules
=======================

Rogue includes a small set of reusable stream modules that cover the most
common stream-graph jobs: buffering, filtering, rate reduction, debug
inspection, and network bridging.

These modules are useful because they let a stream graph be assembled from
well-defined pieces instead of forcing every application to reimplement the same
infrastructure. In practice, many stream topologies are built by combining a
custom ``Master`` or ``Slave`` with one or more of these built-in modules.

Module Overview
===============

The main built-in stream modules are:

- ``Fifo`` for queue-based buffering with optional copy and trim behavior
- ``Filter`` for channel selection and optional dropping of errored ``Frame``
  objects
- ``RateDrop`` for count-based or time-based rate reduction
- Debug ``Slave`` mode for payload inspection without writing a custom receiver
- ``TcpServer`` and ``TcpClient`` for bridging streams across TCP

How To Choose A Module
======================

In most cases, the choice is driven by the specific problem in the stream path:

- If the issue is burstiness or flow-control mismatch, start with ``Fifo``.
- If only one channel or only non-errored traffic should continue downstream,
  use ``Filter``.
- If the downstream path only needs a representative sample of the traffic, use
  ``RateDrop``.
- If the need is simply to inspect bytes or metadata during bring-up, attach a
  debug ``Slave``.
- If the stream must cross a process or machine boundary, use the TCP bridge.

Constructor Quick Reference
===========================

- ``ris.Fifo(maxDepth, trimSize, noCopy)``
- ``ris.Filter(dropErrors, channel)``
- ``ris.RateDrop(period, value)``
- ``ris.TcpServer(addr, port)``
- ``ris.TcpClient(addr, port)``

Each module has its own usage page with fuller discussion and examples.

What To Explore Next
====================

- ``Fifo`` usage: :doc:`/stream_interface/fifo`
- ``Filter`` usage: :doc:`/stream_interface/filter`
- ``RateDrop`` usage: :doc:`/stream_interface/rate_drop`
- Debug ``Slave`` usage: :doc:`/stream_interface/debugStreams`
- TCP bridge usage: :doc:`/stream_interface/tcp_bridge`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/fifo`
  - :doc:`/api/python/rogue/interfaces/stream/filter`
  - :doc:`/api/python/rogue/interfaces/stream/ratedrop`
  - :doc:`/api/python/rogue/interfaces/stream/tcpcore`
  - :doc:`/api/python/rogue/interfaces/stream/tcpclient`
  - :doc:`/api/python/rogue/interfaces/stream/tcpserver`
  - :doc:`/api/python/rogue/interfaces/stream/slave`

- C++:

  - :doc:`/api/cpp/interfaces/stream/fifo`
  - :doc:`/api/cpp/interfaces/stream/filter`
  - :doc:`/api/cpp/interfaces/stream/rateDrop`
  - :doc:`/api/cpp/interfaces/stream/tcpCore`
  - :doc:`/api/cpp/interfaces/stream/tcpClient`
  - :doc:`/api/cpp/interfaces/stream/tcpServer`
  - :doc:`/api/cpp/interfaces/stream/slave`

.. toctree::
   :maxdepth: 1
   :caption: Built-in Stream Modules:

   fifo
   filter
   rate_drop
   tcp_bridge
   debugStreams
