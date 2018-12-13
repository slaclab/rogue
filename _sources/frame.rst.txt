Frames
=====

In the stream interface the Frame class is a container for moving streaming data
through the system. A single Frame instance exists for each frame of data 
being transferred. The frame object itself does not contain any data, instead
it is a container for one or more blocks of data contained within the Buffer class.

The Frame class contains methods for accessing the frame data contained within
the buffers as well as overall information about the frame itself.

.. doxygenclass:: rogue::interfaces::stream::Frame
   :members:


