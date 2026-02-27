.. _protocols_batcher_classes_coreV2:

======
CoreV2
======

``CoreV2`` parses Batcher v2 super-frames and exposes parsed record metadata
through ``Data`` objects plus header/tail iterators.

Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK

CoreV2 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::CoreV2Ptr

The CoreV2 class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::CoreV2
   :members:
