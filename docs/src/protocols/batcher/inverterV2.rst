.. _protocols_batcher_inverterV2:

===========================
Batcher Protocol InverterV2
===========================

``InverterV2`` transforms a Batcher v2 frame in place and forwards a single
output frame.

Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK

Behavior summary
================

* Input is parsed with ``CoreV2``.
* Tail/header data is shifted in place across records.
* Final payload is reduced by one header-width segment.
* Exactly one output frame is emitted for each input frame.
* This is not batching or unbatching; it is a one-frame in-place reformat.

Use ``SplitterV2`` for true unbatching.

Python example
==============

.. code-block:: python

   import rogue.protocols.batcher

   src = MyBatcherV2Source()
   inv = rogue.protocols.batcher.InverterV2()
   dst = MyTransformedFrameSink()

   src >> inv >> dst
