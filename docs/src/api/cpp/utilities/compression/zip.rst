.. _utilities_compression_streamzip:

=========
StreamZip
=========

The StreamZip class provides a payload compression engine for Rogue Frames. This module will receive Frames from
an external master, compress the Frame payload and then pass the compressed frame to a downstream Slave.

This compression module uses the Bzip2 library.

Python binding
==============

This C++ class is also exported into Python as ``rogue.utilities.StreamZip``.

Python API page:
- :doc:`/api/python/utilities_compression_streamzip`

StreamZip objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::utilities::StreamZipPtr

The class description is shown below:

.. doxygenclass:: rogue::utilities::StreamZip
   :members:
