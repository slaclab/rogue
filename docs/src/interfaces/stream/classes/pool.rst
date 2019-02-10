.. _interfaces_stream_pool:

Pool
====

The Pool class is the base class for Buffer and Frame allocation. This base class
supports fully dynamic or fixed size buffer pool mode. Its functions can be 
re-implemented by a sub-class in order to support custom buffer allocation
mechanisms.

Pool objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::PoolPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Pool
   :members:
   :protected-members:

