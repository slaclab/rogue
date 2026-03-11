.. _utilities_fileio_writing:

========================
Writing Frames To A File
========================

``rogue.utilities.fileio.StreamWriter`` captures incoming stream frames into a
Rogue file format that preserves payload bytes plus frame metadata.

For the on-disk format details (header words, channel/flags/error encoding,
raw mode, and split-file behavior), see :ref:`utilities_fileio_format`.

Method Overview
===============

The examples below use a small set of core ``StreamWriter`` methods:

- ``setBufferSize(bytes)``: Sets the in-memory staging buffer used before
  flushing writes to the OS. Larger values can improve throughput.
- ``setMaxSize(bytes)``: Enables split-file output when non-zero
  (``file.dat.1``, ``file.dat.2``, ...), rolling over before a write would
  exceed the limit.
- ``setDropErrors(bool)``: Controls whether incoming frames with non-zero frame
  error are discarded instead of written.
- ``getChannel(index)``: Returns the per-channel stream sink used to attach
  stream sources.
  Channel behavior is special for ``index=0``:
  ``getChannel(0)`` uses each incoming frame's own channel metadata
  (``frame.getChannel()``) when writing the file header.
  ``getChannel(N)`` with ``N>0`` forces file channel ``N`` for all frames sent
  through that sink, regardless of frame metadata.
- ``open(path)``: Opens the output file and starts capture.
- ``close()``: Flushes buffered data and closes the file.

In the PyRogue wrapper flow, the same operations are exposed through tree
variables/commands such as ``DataFile``, ``Open``, and ``Close``.

Logging
=======

The underlying C++ ``StreamWriter`` uses Rogue C++ logging.

- Logger name: ``pyrogue.fileio.StreamWriter``
- Configuration API:
  ``rogue.Logging.setFilter('pyrogue.fileio.StreamWriter', rogue.Logging.Debug)``
- Typical messages: file open/close flow, split-file rollover, and write-path
  operational diagnostics

Set the filter before constructing the writer object.

The PyRogue wrapper itself is primarily a control surface around that C++
writer, so the most useful logging usually comes from the underlying
``StreamWriter`` logger.

Python StreamWriter Example
===========================

.. code-block:: python

   import rogue.utilities.fileio as ruf

   # Assume streamA and streamB are existing stream masters.
   fwrite = ruf.StreamWriter()

   # Buffer size controls staged write size before flushing to the OS.
   fwrite.setBufferSize(10000)

   # Split output file at 100 MB boundaries: myFile.dat.1, .2, ...
   fwrite.setMaxSize(100000000)

   # Drop incoming frames with non-zero frame error.
   fwrite.setDropErrors(True)

   # Map each source to a writer channel.
   streamA >> fwrite.getChannel(0)
   streamB >> fwrite.getChannel(1)

   fwrite.open("myFile.dat")
   # ... stream traffic is captured while file is open ...
   fwrite.close()

PyRogue StreamWriter Device Wrapper
===================================

``pyrogue.utilities.fileio.StreamWriter`` wraps the writer for use in a
``Root`` tree and GUI/client control.

.. code-block:: python

   import pyrogue.utilities.fileio as puf

   # Optional config/status streams can be mapped by channel.
   # Those channels are emitted as YAML metadata on open/close.
   fwrite = puf.StreamWriter(configStream={1: statusStream})
   root.add(fwrite)

   streamA >> fwrite.getChannel(0)
   streamB >> fwrite.getChannel(2)

   # File control can be performed through Device variables/commands.
   fwrite.DataFile.set("myFile.dat")
   fwrite.Open()
   # ...
   fwrite.Close()

C++ StreamWriter Example
========================

.. code-block:: cpp

   #include <rogue/utilities/fileio/StreamWriter.h>
   #include <rogue/utilities/fileio/StreamWriterChannel.h>

   namespace ruf = rogue::utilities::fileio;

   // Assume streamA and streamB are existing stream masters.
   auto fwrite = ruf::StreamWriter::create();

   fwrite->setBufferSize(10000);
   fwrite->setMaxSize(100000000);
   fwrite->setDropErrors(true);

   streamA >> fwrite->getChannel(0);
   streamB >> fwrite->getChannel(1);

   fwrite->open("myFile.dat");
   // ... stream traffic is captured while file is open ...
   fwrite->close();

API Reference
=============

- C++: :doc:`/api/cpp/utilities/fileio/writer`
- Python: :doc:`/api/python/pyrogue/utilities/fileio_streamwriter`
