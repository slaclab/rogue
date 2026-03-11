.. _protocols_batcher_splitter:
.. _protocols_batcher_splitterV1:
.. _protocols_batcher_splitterV2:

=========================
Batcher Protocol Splitter
=========================

The splitter modules accept one batcher super-frame and emit one Rogue stream
frame per contained record (true unbatching).

Use:

- ``SplitterV1`` with batcher v1 framing.
- ``SplitterV2`` with batcher v2 framing.

When to use splitter vs inverter
================================

- Use splitter when downstream stages need record-level routing/filtering.
- Use inverter when downstream expects one transformed super-frame.

Behavior summary
========================

- Input is parsed with ``CoreV1``/``CoreV2``.
- Each parsed ``Data`` record becomes one output frame.
- Output metadata mapping:
  ``channel`` <- destination, ``firstUser`` <- first-user, ``lastUser`` <- last-user.



Python examples
===============

V1
--

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   src = MyBatcherV1Source()
   split = rogue.protocols.batcher.SplitterV1()
   filt = rogue.interfaces.stream.Filter(True, 1)
   dst = MyRecordSink()

   src >> split >> filt >> dst

V2
--

.. code-block:: python

   import rogue.protocols.batcher
   import rogue.interfaces.stream

   src = MyBatcherV2Source()
   split = rogue.protocols.batcher.SplitterV2()
   filt = rogue.interfaces.stream.Filter(True, 3)
   dst = MyRecordSink()

   src >> split >> filt >> dst

Related Topics
==============

- :doc:`/built_in_modules/protocols/batcher/index`

API Reference
=============

- Python:

  - :doc:`/api/python/protocols_batcher_splitterv1`
  - :doc:`/api/python/protocols_batcher_splitterv2`

- C++:

  - :doc:`/api/cpp/protocols/batcher/splitterV1`
  - :doc:`/api/cpp/protocols/batcher/splitterV2`
