.. _interfaces_stream_frame_iterator:

Frame Iterator
==============

The FrameIterator class implements a standard C++ iterator object which is able to
read data from and write data to the Buffers contianed in a Frame. This is the standard
was of accessing data in a :ref:`interfaces_stream_frame`.

The FrameIterator class is also aliased as a Frame::iterator

.. doxygentypedef:: rogue::interfaces::stream::Frame::iterator

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::FrameIterator
   :members:

