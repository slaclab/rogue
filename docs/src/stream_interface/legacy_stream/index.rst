.. _interfaces_stream:

================
Stream Interface
================

The stream interface provides a mechanism for moving bulk data between
modules within Rogue. This interface consists of a Frame container which
contains a series of Buffers which contain the payload data. A stream interface
consists of a Master which is the source of the Rogue Frame and a slave which
is the destination of the Frame.

Conceptual and architectural stream documentation is organized under
:doc:`/stream_interface/index`.

C++ API details for stream classes are documented in
:doc:`/api/cpp/interfaces/stream/index`.

.. toctree::
   :maxdepth: 1
   :caption: Using Streams:

   connecting
   sending
   receiving
   usingTcp
   usingFifo
   usingFilter
   usingRateDrop
   debugStreams
