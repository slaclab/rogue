.. _protocols_batcher_splitter:
.. _protocols_batcher_splitterV1:
.. _protocols_batcher_splitterV2:

=========================
Batcher Protocol Splitter
=========================

For true unbatching of a firmware super-frame into one Rogue frame per record,
Rogue provides ``rogue.protocols.batcher.SplitterV1`` and ``SplitterV2``.

Use a splitter when downstream logic needs ordinary record-sized frames for
filtering, routing, analysis, or file capture.

Version Selection
=================

- Use ``SplitterV1`` with batcher v1 framing.
- Use ``SplitterV2`` with batcher v2 framing.

How Splitting Works
===================

The splitter uses the corresponding parser core to decode one batched frame,
then emits one output frame per parsed record:

- ``SplitterV1`` uses ``CoreV1``.
- ``SplitterV2`` uses ``CoreV2``.

Each parsed ``Data`` record becomes one Rogue output frame. The payload bytes
are copied from the parsed record, and the record metadata is mapped into the
output frame fields.

Output Metadata Mapping
=======================

- Output ``channel`` comes from the record destination.
- Output ``firstUser`` comes from the record first-user metadata.
- Output ``lastUser`` comes from the record last-user metadata.

That mapping is why a splitter is useful for downstream stream processing: once
the super-frame has been split, the downstream path can operate on each record
using the ordinary Rogue stream metadata it already expects.

Splitter vs Inverter
====================

Use a splitter when downstream stages need one frame per record. Use
:doc:`inverter` when downstream expects one transformed super-frame instead.

Python Examples
===============

V1
--

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   # Source produces batcher-v1 super-frames.
   src = MyBatcherV1Source()

   # Split one input super-frame into one output frame per parsed record.
   split = rogue.protocols.batcher.SplitterV1()

   # Keep only record destination 1 after unbatching.
   filt = rogue.interfaces.stream.Filter(True, 1)
   dst = MyRecordSink()

   src >> split >> filt >> dst

V2
--

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   # Source produces batcher-v2 super-frames.
   src = MyBatcherV2Source()

   # Split one input super-frame into one output frame per parsed record.
   split = rogue.protocols.batcher.SplitterV2()

   # Keep only record destination 3 after unbatching.
   filt = rogue.interfaces.stream.Filter(True, 3)
   dst = MyRecordSink()

   src >> split >> filt >> dst

C++ Example
===========

.. code-block:: cpp

   #include <rogue/protocols/batcher/SplitterV1.h>

   namespace rpb = rogue::protocols::batcher;

   int main() {
       // Source produces batcher-v1 super-frames.
       auto src = MyBatchedFrameSource::create();

       // Split one input super-frame into one output frame per parsed record.
       auto split = rpb::SplitterV1::create();
       auto dst = MyRecordSink::create();

       *(*src >> split) >> dst;
       return 0;
   }

Threading And Lifecycle
=======================

The splitter classes do not create worker threads. Splitting runs
synchronously inside ``acceptFrame()`` in the caller thread.

Related Topics
==============

- :doc:`/built_in_modules/protocols/batcher/index`
- :doc:`/built_in_modules/protocols/batcher/inverter`

API Reference
=============

- Python:
  :doc:`/api/python/rogue/protocols/batcher/splitterv1`
  :doc:`/api/python/rogue/protocols/batcher/splitterv2`
- C++:
  :doc:`/api/cpp/protocols/batcher/splitterV1`
  :doc:`/api/cpp/protocols/batcher/splitterV2`
