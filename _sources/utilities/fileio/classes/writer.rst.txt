.. _utilities_fileio_writer:

============
StreamWriter
============

The StreamWriter class is the utilitiy for writing Rogue data to a file. The writer class
can accept streams from multiple sources, with the :ref:`utilities_fileio_writer_channel` serving
as the interface to each incoming stream. This class can be sub-classed to support custom formats,
by overriding the writeFile method.

The default format is the following:

The data file is a written as a series of banks, each associated with a written Frame.
Each bank has a channel and frame flags. The channel is per source and the
lower 24 bits of the incoming Frame flags are used as the flags.

The bank is proceeded by 2 - 32-bit headers to indicate bank information and length:

.. code-block:: c

      headerA:
          31:0  = Length of data block in bytes
      headerB:
         31:24  = Channel ID
         23:16  = Frame error
          15:0  = Frame flags

StreamWriter objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::utilities::fileio::StreamWriterPtr

The class description is shown below:

.. doxygenclass:: rogue::utilities::fileio::StreamWriter
   :members:

