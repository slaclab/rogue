.. _interfaces_stream_buffer:

======
Buffer
======

For conceptual usage, see:

- :doc:`/stream_interface/index`

The list of Buffer objects in a Frame is iterated using a the following typedef:

   rogue::interfaces::stream::Frame::BufferIterator

The uint8_t data within a Buffer is iterated using a the following typedef:

   rogue::interfaces::stream::Buffer::iterator


Buffer objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::BufferPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Buffer
   :members:
