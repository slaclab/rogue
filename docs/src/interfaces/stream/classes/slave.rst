.. _interfaces_stream_slave:

Slave
=====

The stream interface Slave class is the interface for receiving a Frame. Examples of using the
Slave class can be found at :ref:`interfaces_stream_receiving`. Each Slave class object will 
be coupled with one or more :ref:`interfaces_stream_master` objects. 

Slave objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::SlavePtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Slave
   :members:

