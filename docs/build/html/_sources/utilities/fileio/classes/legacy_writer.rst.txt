.. _utilities_fileio_legacy_writer:

==================
LegacyStreamWriter
==================

The LegacyStreamWriter class is the utilitiy for writing Rogue data to a file, using a file format
used in the older XmlDaq platform. The writer class can accept streams from multiple sources,
with the :ref:`utilities_fileio_writer_channel` serving as the interface to each incoming stream.

LegacyStreamWriter objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::utilities::fileio::LegacyStreamWriterPtr

The class description is shown below:

.. doxygenclass:: rogue::utilities::fileio::LegacyStreamWriter
   :members:

