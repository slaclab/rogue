.. _interfaces_stream_frame:

=====
Frame
=====

For conceptual guidance on stream architecture and pipeline usage, see:

- :doc:`/stream_interface/index`
- :doc:`/stream_interface/frame_model`
- :doc:`/stream_interface/connecting`

Python binding
--------------

This C++ class is also exported into Python as ``rogue.interfaces.stream.Frame``.

Python API page:
- :doc:`/api/python/rogue/interfaces/stream/frame`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::FramePtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::Frame
   :members:
