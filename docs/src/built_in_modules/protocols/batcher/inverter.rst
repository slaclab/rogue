.. _protocols_batcher_inverter:
.. _protocols_batcher_inverterV1:
.. _protocols_batcher_inverterV2:

=========================
Batcher Protocol Inverter
=========================

The inverter modules transform a batcher super-frame in place and forward a
single output frame. They are not batching or unbatching stages.

Use:

- ``InverterV1`` with batcher v1 framing.
- ``InverterV2`` with batcher v2 framing.

When to use inverter vs splitter
================================

- Use inverter when downstream expects one transformed super-frame.
- Use splitter when downstream expects one frame per logical record.

Version behavior summary
========================

InverterV1
----------

- Input is parsed with ``CoreV1``.
- Tail/header data is shifted in place across records.
- Final payload is reduced by one tail-width segment.
- Exactly one output frame is emitted for each input frame.

InverterV2
----------

- Input is parsed with ``CoreV2``.
- Tail/header data is shifted in place across records.
- Final payload is reduced by one header-width segment.
- Exactly one output frame is emitted for each input frame.

Python examples
===============

V1
--

.. code-block:: python

   import rogue.protocols.batcher

   src = MyBatcherV1Source()
   inv = rogue.protocols.batcher.InverterV1()
   dst = MyTransformedFrameSink()

   src >> inv >> dst

V2
--

.. code-block:: python

   import rogue.protocols.batcher

   src = MyBatcherV2Source()
   inv = rogue.protocols.batcher.InverterV2()
   dst = MyTransformedFrameSink()

   src >> inv >> dst

Related Topics
==============

- :doc:`/built_in_modules/protocols/batcher/index`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/protocols/batcher/inverterv1`
  - :doc:`/api/python/rogue/protocols/batcher/inverterv2`

- C++:

  - :doc:`/api/cpp/protocols/batcher/inverterV1`
  - :doc:`/api/cpp/protocols/batcher/inverterV2`
