.. _protocols_batcher_classes_coreV1:

======
CoreV1
======

``CoreV1`` parses Batcher v1 super-frames and exposes parsed record metadata
through ``Data`` objects plus header/tail iterators.

Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg


CoreV1 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::CoreV1Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::CoreV1
   :members:
