.. _protocols_batcher_classes_data:

====
Data
====

``Data`` describes one parsed record in a Batcher super-frame, including
payload iterator range and per-record metadata (destination and user bytes).
It is produced by ``CoreV1/CoreV2`` and consumed by ``SplitterV1/SplitterV2``.
For conceptual guidance, see :doc:`/built_in_modules/protocols/batcher/index`.


Data objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::DataPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::Data
   :members:
