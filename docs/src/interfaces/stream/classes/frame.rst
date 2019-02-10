.. _interfaces_stream_frame:

Frame
=====

In the stream interface the Frame class is a container for moving streaming data
through the system. A single Frame instance exists for each frame of data 
being transferred. The frame object itself does not contain any data, instead
it is a container for one or more blocks of data contained within the :ref:`interfaces_stream_buffer` class.

Frame data access in C++ uses a :ref:`interfaces_stream_frame_iterator` object, which operations
as a standard C++ iteration object. Frames are usually accessed in write mode starting with a
newly created Frame in a stream Master, or in read mode when receiving a Frame in a stream Slave.

Frame objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::FramePtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Frame
   :members:

