.. _protocols_batcher_inverterV1:

===========================
Batcher Protocol InverterV1
===========================

``InverterV1`` transforms a Batcher v1 frame in place and forwards a single
output frame.

Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg

Behavior summary
================

* Input is parsed with ``CoreV1``.
* Tail/header data is shifted in place across records.
* Final payload is reduced by one tail-width segment.
* Exactly one output frame is emitted for each input frame.
* This is not batching or unbatching; it is a one-frame in-place reformat.

Use this when downstream expects the transformed layout rather than
split-per-record output. Use ``SplitterV1`` for true unbatching.

Python example
==============

.. code-block:: python

   import rogue.protocols.batcher

   src = MyBatcherV1Source()
   inv = rogue.protocols.batcher.InverterV1()
   dst = MyTransformedFrameSink()

   src >> inv >> dst
