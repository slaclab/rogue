.. _protocols_batcher_splitterV1:

===========================
Batcher Protocol SplitterV1
===========================

``SplitterV1`` accepts one Batcher v1 super-frame and emits one Rogue stream
frame per contained record.

Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg

Behavior summary
================

* Input is parsed with ``CoreV1``.
* Each parsed ``Data`` record becomes one output frame.
* Output frame metadata is mapped as:

  * ``channel`` <- record destination
  * ``firstUser`` <- record first-user byte
  * ``lastUser`` <- record last-user byte

Use this when you want normal per-record frame handling downstream.

Python example
==============

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   src = MyBatcherV1Source()
   split = rogue.protocols.batcher.SplitterV1()
   filt = rogue.interfaces.stream.Filter(True, 1)  # Keep destination/channel 1
   dst = MyRecordSink()

   src >> split >> filt >> dst

