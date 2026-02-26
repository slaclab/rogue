.. _utilities_compression_streamunzip:

===========
StreamUnZip
===========

The StreamUnZip class provides a payload decompression engine for Rogue Frames. This module will receive compressed
Frames from an external master, de-compress the Frame payload and then pass the compressed frame to a downstream Slave.

This de-compression module uses the Bzip2 library.


.. doxygentypedef:: rogue::utilities::StreamUnZipPtr

.. doxygenclass:: rogue::utilities::StreamUnZip
   :members:
