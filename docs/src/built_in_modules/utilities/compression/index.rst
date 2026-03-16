.. _utilities_compression:

=====================
Compression Utilities
=====================

Compression utilities provide stream modules for in-line payload compression
and decompression.

C++ API details for compression utilities are documented in
:doc:`/api/cpp/utilities/compression/index`.

Use these modules when transport bandwidth or storage size is constrained and
both ends of the pipeline agree on compressed payload handling.

These modules are most useful when compression is just one stage in a larger
stream graph. Typical use cases include:

- Compressing captured data before writing it to disk.
- Reducing bandwidth on a software transport path between processes or hosts.
- Replaying stored compressed files back into analysis or verification
  pipelines.

The important design point is that Rogue compression operates on frame payloads
inside the stream graph. That makes it easy to insert between an existing
producer and consumer without redesigning the rest of the topology.

Choosing Compress vs Decompress
===============================

- Use :doc:`compress` when the upstream path produces uncompressed frames and a
  downstream transport or storage layer expects compressed payloads.
- Use :doc:`decompress` when the input stream already contains compressed Rogue
  frame payloads and downstream consumers expect the original bytes.

These are usually used as paired stages across a capture/replay or
transport/receive boundary.

What To Explore Next
====================

- In-line compression pipelines: :doc:`compress`
- Restoring compressed payloads: :doc:`decompress`
- File capture and replay workflows: :doc:`/built_in_modules/utilities/fileio/index`
- General stream composition patterns: :doc:`/stream_interface/index`

.. toctree::
   :maxdepth: 1
   :caption: Compression Utilities:

   compress
   decompress
