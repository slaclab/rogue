.. _stream_interface_docs:
.. _stream_interface_overview:
.. _interfaces_stream:

================
Stream Interface
================

The stream interface is Rogue's bulk-data path for moving ``Frame`` objects
between modules. A ``Master`` produces ``Frame`` objects, one or more
``Slave`` objects consume them, and the stream graph between them can be
composed from reusable buffering, filtering, rate-control, debug, and bridge
modules.

You use the stream interface when the application needs to move payload-oriented
data rather than register transactions. Typical examples include acquisition
pipelines, decoder chains, packet processing, diagnostic monitor branches, file
capture, and network export of streaming data. Instead of writing one large
processing loop, you connect small stream components that each perform one job.

Quick Connection Example
========================

.. code-block:: python

   import rogue.interfaces.stream as ris

   src = MyCustomMaster()
   fifo = ris.Fifo(100, 0, True)
   rate = ris.RateDrop(True, 0.1)  # Keep at most one Frame every 0.1 s
   dst = MyCustomSlave()

   src >> fifo >> rate >> dst

In this chain, ``Fifo`` absorbs bursts by queuing incoming ``Frame`` objects
and ``RateDrop`` reduces how often the downstream ``Slave`` receives traffic.
This is a common pattern when the producer runs faster than a monitor, logger,
or analysis stage.

Connection Model
================

Rogue overloads a few operators to make stream topology construction concise:

- ``master >> slave`` creates a one-way connection
- ``slave << master`` creates the same one-way connection with reversed syntax
- ``endpointA == endpointB`` creates a bi-directional connection for endpoints
  that implement both ``Master`` and ``Slave`` behavior

A single ``Master`` can connect to multiple downstream ``Slave`` objects. The
first attached ``Slave`` becomes the primary ``Slave``. That matters because
the primary ``Slave`` services ``reqFrame()`` allocation requests, and
``sendFrame()`` delivers to secondary ``Slave`` objects before the primary one.
That ordering is important when the primary path consumes or empties a
zero-copy ``Frame``.

Implementation Model
====================

The stream interface implementation lives in C++ for performance and predictable
threaded behavior. Rogue exposes these classes to Python, so stream topologies
can be built and orchestrated in Python while the high-rate transport and
processing path remains in C++.

That split makes a practical workflow possible:

1. Build and connect the stream graph in Python first.
2. Validate the topology with realistic traffic and debugging tools.
3. Move only the bottleneck stages into C++ when measurements justify it.

Core Types
==========

Three types appear throughout the stream interface:

- ``Master`` is the source endpoint that allocates and transmits ``Frame``
  objects.
- ``Slave`` is the sink endpoint that receives ``Frame`` objects and may also
  participate in ``Frame`` allocation.
- ``Frame`` is the payload and metadata container that moves through the graph.

A ``Frame`` payload may span multiple underlying ``Buffer`` objects. In C++,
``FrameIterator`` lets code traverse those bytes without manually managing
buffer boundaries.

What To Explore Next
====================

- Connection semantics: :doc:`/stream_interface/connecting`
- ``Frame`` semantics and metadata: :doc:`/stream_interface/frame_model`
- Custom transmitters: :doc:`/stream_interface/sending`
- Custom receivers: :doc:`/stream_interface/receiving`
- Built-in stream modules: :doc:`/stream_interface/built_in_modules`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/master`
  - :doc:`/api/python/rogue/interfaces/stream/slave`
  - :doc:`/api/python/rogue/interfaces/stream/frame`

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
   /custom_module/index
