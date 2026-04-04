.. _protocols_batcher_combiner:
.. _protocols_batcher_combinerV1:
.. _protocols_batcher_combinerV2:

==========================
Batcher Protocol Combiner
==========================

For building batcher super-frames in software from individual Rogue stream
frames, Rogue provides ``rogue.protocols.batcher.CombinerV1`` and
``CombinerV2``. These are the software equivalents of the firmware batcher and
the inverse of the splitter classes.

Use a combiner when you need to produce batched super-frames in software,
for example to emulate firmware batching in test setups, or to generate
controlled inputs for CI regression testing of the unbatcher (splitter)
classes.

Version Selection
=================

- Use ``CombinerV1`` to produce batcher v1 super-frames.
- Use ``CombinerV2`` to produce batcher v2 super-frames.

How Combining Works
===================

The combiner operates in two phases:

1. **Queue** -- Individual frames are accepted via the stream slave interface
   (``acceptFrame()``). Each frame's payload, channel, firstUser, and lastUser
   are preserved in the queue.

2. **Batch** -- Calling ``sendBatch()`` builds a single batcher super-frame
   containing all queued frames, writes the appropriate super-header and
   per-record tails, and emits the super-frame downstream.

``CombinerV1`` writes the width-dependent header and tail padding required by
the v1 protocol. The ``width`` constructor parameter controls the AXI stream
width encoding (0 = 16-bit through 5 = 512-bit).

``CombinerV2`` writes the fixed 2-byte header and 7-byte per-record tails
defined by the v2 protocol.

Round-Trip Guarantee
====================

A combiner followed by the matching splitter reproduces the original frames:

- Payload bytes are identical.
- Channel, firstUser, and lastUser metadata are preserved.

This makes the combiner useful as a test fixture for CI regression testing
of the splitter and inverter classes.

Python Examples
===============

V1
--

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   # Build a batcher v1 super-frame from individual frames.
   combiner = rogue.protocols.batcher.CombinerV1(2)  # width=2 -> 64-bit

   # Downstream splitter to verify round-trip.
   splitter = rogue.protocols.batcher.SplitterV1()
   dst = MyRecordSink()

   src >> combiner
   combiner >> splitter >> dst

   # Queue frames, then batch and send.
   combiner.sendBatch()

V2
--

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   # Build a batcher v2 super-frame from individual frames.
   combiner = rogue.protocols.batcher.CombinerV2()

   # Downstream splitter to verify round-trip.
   splitter = rogue.protocols.batcher.SplitterV2()
   dst = MyRecordSink()

   src >> combiner
   combiner >> splitter >> dst

   # Queue frames, then batch and send.
   combiner.sendBatch()

C++ Example
===========

.. code-block:: cpp

   #include <rogue/protocols/batcher/CombinerV1.h>
   #include <rogue/protocols/batcher/SplitterV1.h>

   namespace rpb = rogue::protocols::batcher;

   int main() {
       // Width=2 -> 64-bit AXI stream.
       auto combiner = rpb::CombinerV1::create(2);
       auto splitter = rpb::SplitterV1::create();
       auto dst = MyRecordSink::create();

       *(*combiner >> splitter) >> dst;

       // After queuing frames via the stream interface:
       combiner->sendBatch();
       return 0;
   }

Threading And Lifecycle
=======================

The combiner classes do not create worker threads. Frame queueing runs
synchronously inside ``acceptFrame()``, and batch building runs
synchronously inside ``sendBatch()``.

Related Topics
==============

- :doc:`/built_in_modules/protocols/batcher/index`
- :doc:`/built_in_modules/protocols/batcher/splitter`

API Reference
=============

- Python:
  :doc:`/api/python/rogue/protocols/batcher/combinerv1`
  :doc:`/api/python/rogue/protocols/batcher/combinerv2`
- C++:
  :doc:`/api/cpp/protocols/batcher/combinerV1`
  :doc:`/api/cpp/protocols/batcher/combinerV2`
