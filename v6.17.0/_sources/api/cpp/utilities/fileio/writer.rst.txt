.. _utilities_fileio_writer:

============
StreamWriter
============

The StreamWriter class writes Rogue stream frames to disk. It can accept frames
from multiple incoming sources, with :ref:`utilities_fileio_writer_channel`
providing the per-channel input interfaces. This class can be sub-classed to
support custom formats by overriding ``writeFile()``.

The shared on-disk record format (headers and metadata field encoding) is
documented here:

- :ref:`utilities_fileio_format`

For conceptual utility usage, see:

- :doc:`/built_in_modules/utilities/fileio/index`

Raw Mode
========

When ``setRaw(True)`` is enabled, StreamWriter writes only payload bytes for
each frame and omits per-record headers. In this mode, channel/error/flags
metadata is not persisted.

File Splitting Behavior
=======================

If ``setMaxSize()`` is non-zero, StreamWriter rolls to a new output file before
writing a record that would exceed the configured limit.

Split files use incrementing numeric suffixes:

.. code-block:: text

   myFile.dat.1
   myFile.dat.2
   myFile.dat.3

Every file is opened as a new file. ``open()`` throws ``rogue::GeneralError``
if the target path (``myFile.dat``, or ``myFile.dat.1`` when splitting is
enabled) already exists, and the writer remains closed. Likewise, if the next
split file already exists when a rollover is needed, the write throws and the
writer closes instead of writing into the existing file. An existing data file
is never truncated or appended to.


StreamWriter objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::utilities::fileio::StreamWriterPtr

The class description is shown below:

.. doxygenclass:: rogue::utilities::fileio::StreamWriter
   :members:
