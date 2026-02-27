.. _protocols_batcher_splitterV2:

===========================
Batcher Protocol SplitterV2
===========================

``SplitterV2`` accepts one Batcher v2 super-frame and emits one Rogue stream
frame per contained record.

Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK

Behavior summary
================

* Input is parsed with ``CoreV2``.
* Each parsed ``Data`` record becomes one output frame.
* Output frame metadata is mapped as:
  ``channel`` <- destination, ``firstUser`` <- first-user, ``lastUser`` <- last-user.

Python example
==============

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   src = MyBatcherV2Source()
   split = rogue.protocols.batcher.SplitterV2()
   filt = rogue.interfaces.stream.Filter(True, 3)  # Keep destination/channel 3
   dst = MyRecordSink()

   src >> split >> filt >> dst
