.. _interfaces_stream_frame:

Frame
=====

In the stream interface the Frame class is a container for moving streaming data
through the system. A single Frame instance exists for each frame of data 
being transferred. The frame object itself does not contain any data, instead
it is a container for one or more blocks of data contained within the :ref:`interfaces_stream_buffer` class.

Because the underlying Buffers may have been received from protocol modules which add and
removed protocol header and tail data, the Buffer class has the ability to adjust the
header and tail reservation. This adjustment is made by protocol modules as Frame data
moves through the Rogue system. More information about the header and tail reservations
can be found in the :ref:`interfaces_stream_buffer` class description.

Frame data access in C++ uses a :ref:`interfaces_strea_frame_iterator` object, which operations
as a standard C++ iteration object. Frames are usually accessed in write mode starting with a
newly created Frame in a stream Master, or in read mode when receiving a Frame in a stream Slave.

.. doxygenclass:: rogue::interfaces::stream::Frame
   :members:

