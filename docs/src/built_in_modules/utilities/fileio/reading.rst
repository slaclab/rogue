.. _utilities_fileio_reading:

==========================
Reading Frames From A File
==========================

``rogue.utilities.fileio.StreamReader`` replays captured Rogue files as stream
frames. Frame metadata (channel, flags, error) is reconstructed and propagated
with each emitted frame.

Frames can be read in a streaming fashion using ``StreamReader``. Each data
record is emitted as a Rogue ``Frame`` with payload and metadata preserved from
the original file capture. If multiple channels were used during writing, the
replayed frames retain those channel IDs. A stream filter stage can then route
replayed frames by channel as needed.

For file-format details consumed by the reader, see
:ref:`utilities_fileio_format`.

Method Overview
===============

The examples below use the core ``StreamReader`` methods:

- ``open(path)``: Opens an input file and starts background replay.
- ``closeWait()``: Blocks until replay finishes, then closes the reader.
- ``close()``: Stops replay immediately and closes the reader.

When the input name ends with ``.1``, the reader automatically attempts
``.2``, ``.3``, and so on as a split-file sequence.

Logging
=======

``StreamReader`` does not expose a dedicated file-reader logger in the same way
that ``StreamWriter`` does.

For replay debugging, the practical approaches are:

- Attach a downstream debug ``Slave`` and use ``setDebug(maxBytes, name)`` to
  inspect replayed frames.
- Use application-level logging in the downstream stream consumer if replay
  behavior needs to be correlated with higher-level processing.

See :doc:`/stream_interface/debugStreams` for the standard debug-tap pattern.

Python StreamReader Example
===========================

.. code-block:: python

   import rogue.utilities.fileio as ruf

   # Create the file-to-stream replay source.
   fread = ruf.StreamReader()

   # Connect reader output to an existing stream slave.
   fread >> receiver

   # Opening .1 auto-advances through split files (.2, .3, ...).
   fread.open("myFile.dat.1")
   fread.closeWait()

   # Or call close() for immediate stop.
   # fread.close()

PyRogue StreamReader Device Wrapper
===================================

``pyrogue.utilities.fileio.StreamReader`` wraps the reader for use in a
``Root`` tree and GUI/client control.

.. code-block:: python

   import pyrogue.utilities.fileio as puf

   # Add a tree-managed reader so file replay can be controlled by clients/GUI.
   fread = puf.StreamReader()
   root.add(fread)

   # Route replayed frames to a downstream stream consumer.
   fread >> receiver

   # Configure and run replay via Device variables/commands.
   fread.DataFile.set("myFile.dat.1")
   fread.Open()
   fread.Close()

C++ StreamReader Example
========================

.. code-block:: cpp

   #include <rogue/utilities/fileio/StreamReader.h>

   namespace ruf = rogue::utilities::fileio;

   // Create the file-to-stream replay source.
   auto fread = ruf::StreamReader::create();

   // Connect reader output to an existing stream slave.
   fread >> receiver;

   // Open split-file sequence and wait for completion.
   fread->open("myFile.dat.1");
   fread->closeWait();

API Reference
=============

- C++: :doc:`/api/cpp/utilities/fileio/reader`
- Python: :doc:`/api/python/utilities_fileio_streamreader`
