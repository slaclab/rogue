.. _protocols_batcher_inverter:
.. _protocols_batcher_inverterV1:

=========================
Batcher Protocol Inverter
=========================

For in-place transformation of batched v1 super-frames, Rogue provides
``rogue.protocols.batcher.InverterV1``. This class is not an unbatcher: each
input frame produces exactly one output frame.

Use the inverter when the downstream stage still wants one super-frame-shaped
message, but needs the framing rewritten into the layout expected by that
consumer.

Version Selection
=================

- Use ``InverterV1`` with batcher v1 framing.
- There is no v2 inverter. The v2 format has a fixed 2-byte header and a fixed
  7-byte tail, so the in-place transform described below is not defined for
  it. Use :doc:`splitter` to unbatch v2 frames.

How Inversion Works
===================

The inverter uses ``CoreV1`` to locate record boundaries and tail metadata,
then rewrites the frame in place. The transform requires the header and tail
to have the same width. In v1 the header width equals the AXI stream width and
the tail is at least 8 bytes, so this holds for 64-bit and wider interfaces.
Frames whose header and tail widths differ are dropped.

One input frame yields one output frame. No record fan-out occurs. Instead,
each record's tail is copied into the header or tail slot that precedes it,
and the payload is trimmed to remove the final tail-width segment that has been
folded into the transformed layout.

Inverter vs Splitter
====================

Use an inverter when downstream expects one transformed super-frame. Use
:doc:`splitter` when downstream expects one frame per logical record.

Python Example
==============

.. code-block:: python

   import rogue.protocols.batcher

   # Source produces batcher-v1 super-frames.
   src = MyBatcherV1Source()

   # Rewrite framing in place and keep one output frame per input frame.
   inv = rogue.protocols.batcher.InverterV1()
   dst = MyTransformedFrameSink()

   src >> inv >> dst

C++ Example
===========

.. code-block:: cpp

   #include <rogue/protocols/batcher/InverterV1.h>

   namespace rpb = rogue::protocols::batcher;

   int main() {
       // Source produces batcher-v1 super-frames.
       auto src = MyBatchedFrameSource::create();

       // Rewrite framing in place and keep one output frame per input frame.
       auto inv = rpb::InverterV1::create();
       auto dst = MyTransformedFrameSink::create();

       *(*src >> inv) >> dst;
       return 0;
   }

Threading And Lifecycle
=======================

The inverter does not create worker threads. Frame transformation runs
synchronously inside ``acceptFrame()`` in the caller thread.

Related Topics
==============

- :doc:`/built_in_modules/protocols/batcher/index`
- :doc:`/built_in_modules/protocols/batcher/splitter`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/batcher/inverterv1`
- C++: :doc:`/api/cpp/protocols/batcher/inverterV1`
