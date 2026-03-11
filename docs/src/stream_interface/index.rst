.. _stream_interface_docs:
.. _stream_interface_overview:
.. _interfaces_stream:

================
Stream Interface
================

The stream interface is Rogue's bulk-data path for moving frame-based payloads
between modules. A ``Master`` produces
:ref:`frames <interfaces_stream_frame>`, and one or more ``Slave`` endpoints
consume them.

Streams give you a composable way to build software dataflows: acquisition
pipelines, decode/transform stages, fan-out monitor paths, network bridges,
and rate-controlled or filtered side channels. Instead of hard-wiring one large
processing loop, you connect focused modules that each do one job well.

Quick connection example
========================

.. code-block:: python

   import rogue.interfaces.stream as ris

   src = MyCustomMaster()
   fifo = ris.Fifo(100, 0, True)
   rate = ris.RateDrop(True, 0.1)  # Keep at most one frame every 0.1 s (10 Hz)
   dst = MyCustomSlave()

   src >> fifo >> rate >> dst

In this chain, ``Fifo`` smooths bursty traffic by queuing frames, and
``RateDrop`` enforces a lower output rate before frames reach the final
consumer. This pattern is useful when upstream data production is faster than a
downstream processing or monitoring stage.

Rogue overloads a few operators to make topology construction concise:
``master >> slave`` and ``slave << master`` create one-way links, while
``endpointA == endpointB`` creates a bi-directional connection for endpoints
that implement both stream-master and stream-slave behavior.

For ``ris.Fifo(maxDepth, trimSize, noCopy)``:

- ``maxDepth``: queue depth threshold in frames. If non-zero, incoming frames
  are dropped once the FIFO reaches this depth.
- ``trimSize``: copy-size limit in bytes when ``noCopy`` is ``False``. ``0``
  means copy the full payload.
- ``noCopy``: if ``True``, enqueue the original frame object (no payload copy,
  ``trimSize`` ignored). If ``False``, allocate and copy into a new frame.

For ``ris.RateDrop(period, value)``:

- ``period``: selects mode.
  ``True`` means time-period mode; ``False`` means count mode.
- ``value``:
  if ``period=True``, interpreted as seconds between forwarded frames
  (for example, ``0.1`` gives about 10 Hz).
  if ``period=False``, interpreted as a drop-count setting, where one frame is
  forwarded and then roughly ``value`` frames are suppressed before forwarding
  again.

Implementation model
====================

The stream interface implementation is in C++ for performance and deterministic
threaded behavior. Rogue exposes these classes to Python via bindings, so you
can compose and orchestrate stream topologies in Python while keeping the
high-rate transport and processing path in C++.

Python bindings are typically used for:

- Rapid bring-up and topology prototyping
- Scripted integration testing and validation harnesses
- Hybrid systems where orchestration is in Python and throughput-critical path
  stays in C++

Practical workflow:

1. Build and connect stream modules in Python first.
2. Validate behavior with realistic traffic and instrumentation.
3. Move only bottleneck stages to C++ when needed.

Class-by-class C++ API details are in :doc:`/api/cpp/interfaces/stream/index`.
Python API reference starts at :doc:`/api/python/index`.

Core objects
============

- ``Master``: source endpoint that allocates and transmits frames.
- ``Slave``: sink endpoint that receives frames and can also provide frame
  allocation through the pool interface.
- ``Frame``: payload + metadata container (flags, channel, error).

Frame model
===========

A frame payload may span multiple underlying buffers. In C++,
:ref:`interfaces_stream_frame_iterator` iterates payload bytes across buffer
boundaries without manual segment management.

Frame semantics and APIs are summarized in :doc:`/stream_interface/frame_model`.

Connection model
================

A single ``Master`` can connect to multiple slaves.

- The first attached slave is primary.
- The primary slave services ``reqFrame()`` allocation requests.
- ``sendFrame()`` forwards to all attached slaves, with the primary slave
  receiving last.

That ordering is important when the primary path may consume or empty a frame
(for example, zero-copy sinks).

What To Explore Next
====================

- Connection semantics: :doc:`/stream_interface/connecting`
- Frame semantics and APIs: :doc:`/stream_interface/frame_model`
- Custom transmitters: :doc:`/stream_interface/sending`
- Custom receivers: :doc:`/stream_interface/receiving`
- Built-in modules: :doc:`/stream_interface/built_in_modules`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream_master`
  - :doc:`/api/python/rogue/interfaces/stream_slave`
  - :doc:`/api/python/rogue/interfaces/stream_frame`

- C++:

  - :doc:`/api/cpp/interfaces/stream/master`
  - :doc:`/api/cpp/interfaces/stream/slave`
  - :doc:`/api/cpp/interfaces/stream/frame`

.. toctree::
   :maxdepth: 1
   :caption: Stream Interface:

   connecting
   frame_model
   sending
   receiving
   built_in_modules
   fifo
   filter
   rate_drop
   tcp_bridge
   debugStreams
   /custom_module/index
