.. _protocols_batcher_inverter:
.. _protocols_batcher_inverterV1:
.. _protocols_batcher_inverterV2:

=========================
Batcher Protocol Inverter
=========================

For in-place transformation of batched super-frames, Rogue provides
``rogue.protocols.batcher.InverterV1`` and ``InverterV2``. These classes are
not unbatchers: each input frame produces exactly one output frame.

Use an inverter when the downstream stage still wants one super-frame-shaped
message, but needs the framing rewritten into the layout expected by that
consumer.

Version Selection
=================

- Use ``InverterV1`` with batcher v1 framing.
- Use ``InverterV2`` with batcher v2 framing.

How Inversion Works
===================

The inverter uses the corresponding parser core to locate record boundaries and
tail metadata, then rewrites the frame in place:

- ``InverterV1`` uses ``CoreV1``.
- ``InverterV2`` uses ``CoreV2``.

In both cases, one input frame yields one output frame. No record fan-out
occurs. Instead, the framing information is shifted into the layout expected by
the downstream consumer, and the payload is trimmed to remove the final framing
segment that has been folded into the transformed layout.

Version Behavior
================

``InverterV1`` rewrites batcher v1 framing by copying per-record tail fields
into the positions expected by downstream consumers and trimming the final
tail-width segment from the payload.

``InverterV2`` performs the same overall role for the v2 format, trimming the
final header-width segment after the in-place framing transform.

Inverter vs Splitter
====================

Use an inverter when downstream expects one transformed super-frame. Use
:doc:`splitter` when downstream expects one frame per logical record.

Python Examples
===============

V1
--

.. code-block:: python

   import rogue.protocols.batcher

   # Source produces batcher-v1 super-frames.
   src = MyBatcherV1Source()

   # Rewrite framing in place and keep one output frame per input frame.
   inv = rogue.protocols.batcher.InverterV1()
   dst = MyTransformedFrameSink()

   src >> inv >> dst

V2
--

.. code-block:: python

   import rogue.protocols.batcher

   # Source produces batcher-v2 super-frames.
   src = MyBatcherV2Source()

   # Rewrite framing in place and keep one output frame per input frame.
   inv = rogue.protocols.batcher.InverterV2()
   dst = MyTransformedFrameSink()

   src >> inv >> dst

C++ Example
===========

.. code-block:: cpp

   #include <rogue/protocols/batcher/InverterV2.h>

   namespace rpb = rogue::protocols::batcher;

   int main() {
       // Source produces batcher-v2 super-frames.
       auto src = MyBatchedFrameSource::create();

       // Rewrite framing in place and keep one output frame per input frame.
       auto inv = rpb::InverterV2::create();
       auto dst = MyTransformedFrameSink::create();

       *(*src >> inv) >> dst;
       return 0;
   }

Threading And Lifecycle
=======================

The inverter classes do not create worker threads. Frame transformation runs
synchronously inside ``acceptFrame()`` in the caller thread.

Related Topics
==============

- :doc:`/built_in_modules/protocols/batcher/index`
- :doc:`/built_in_modules/protocols/batcher/splitter`

API Reference
=============

- Python:
  :doc:`/api/python/rogue/protocols/batcher/inverterv1`
  :doc:`/api/python/rogue/protocols/batcher/inverterv2`
- C++:
  :doc:`/api/cpp/protocols/batcher/inverterV1`
  :doc:`/api/cpp/protocols/batcher/inverterV2`
