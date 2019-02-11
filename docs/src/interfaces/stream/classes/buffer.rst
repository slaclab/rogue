.. _interfaces_stream_buffer:

Buffer
======

A Buffer is a class which wraps a raw block of memory. One or more Buffer objects
will make up a Frame. The Buffer object supports the ability to reserve header
and tail space for protocol layers which will process the Buffer data. Interaction with
the Buffer class is for advanced developers. Most users will interact with Frame and Buffer
data using the :ref:`interfaces_stream_frame_iterator` class.

The list of Buffer objects in a Frame is iterated using a the following typedef:

.. doxygentypedef:: rogue::interfaces::stream::Frame::BufferIterator

The uint8_t data within a Buffer is iterated using a the following typedef:

.. doxygentypedef:: rogue::interfaces::stream::Buffer::iterator

Buffer objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::BufferPtr

The Buffer class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Buffer
   :members:
