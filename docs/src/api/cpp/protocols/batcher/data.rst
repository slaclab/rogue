.. _protocols_batcher_classes_data:

====
Data
====

``Data`` describes one parsed record in a Batcher super-frame, including
payload iterator range and per-record metadata (destination and user bytes).
It is produced by ``CoreV1/CoreV2`` and consumed by ``SplitterV1/SplitterV2``.


.. doxygentypedef:: rogue::protocols::batcher::DataPtr

.. doxygenclass:: rogue::protocols::batcher::Data
   :members:
