.. _interfaces_stream_master:

Master
======

The stream interface Master class is the interface for sending a Frame. Examples of using the
Master class can be found at :ref:`interfaces_stream_sending`. Each Master class object will 
be coupled with one or more :ref:`interfaces_stream_slave` objects.

Master objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::MasterPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Master
   :members:

