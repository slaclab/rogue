.. _utilities_compression:

=====================
Compression Utilities
=====================

For in-line compression or decompression inside a Rogue stream graph, Rogue
provides ``rogue.utilities.StreamZip`` and ``rogue.utilities.StreamUnZip``.

These utilities operate on frame payload bytes inside the stream pipeline. That
makes them useful when you want to reduce storage or transport bandwidth and
then restore the original payload later without redesigning the rest of the
graph.

They are most useful when compression is just one stage in a larger workflow.
Common use cases include:

- Compressing captured data before writing it to disk.
- Reducing bandwidth between software or hardware-connected stages.
- Replaying previously compressed files back into an analysis or verification
  chain.

The important design point is that Rogue compression transforms only the frame
payload. The stream metadata remains intact, so the compressor or decompressor
can be inserted between an existing producer and consumer with minimal graph
changes.

Subtopics
=========

- :doc:`compress`
  Use ``StreamZip`` when the upstream path produces uncompressed frames.
- :doc:`decompress`
  Use ``StreamUnZip`` when the input stream already contains compressed Rogue
  frame payloads.

How These Utilities Behave
==========================

Both utilities preserve frame metadata while transforming payload bytes. Both
allocate new output frames as needed. Neither utility starts an internal worker
thread, so compression and decompression run synchronously in
``acceptFrame()``.

That makes them easy to insert into an existing graph, but it also means the
CPU work happens in the calling thread.

Related Topics
==============

- :doc:`/built_in_modules/utilities/fileio/index`
- :doc:`/stream_interface/index`

.. toctree::
   :maxdepth: 1
   :caption: Compression Utilities

   compress
   decompress
