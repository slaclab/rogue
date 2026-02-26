.. _utilities_fileio_writer:

.. note::
   Canonical generated C++ API docs are centralized at :ref:`api_reference`.

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


