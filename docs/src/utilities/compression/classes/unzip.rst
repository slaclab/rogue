.. _utilities_compression_streamunzip:

===========
StreamUnZip
===========

The StreamUnZip class provides a payload decompression engine for Rogue Frames. This module will receive compressed
Frames from an external master, de-compress the Frame payload and then pass the compressed frame to a downstream Slave.

This de-compression module uses the Bzip2 library.

StreamUnZip objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::utilities::StreamUnZipPtr

The class description is shown below:

.. doxygenclass:: rogue::utilities::StreamUnZip
   :members:

