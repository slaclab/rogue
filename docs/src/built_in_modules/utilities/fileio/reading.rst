.. _utilities_fileio_reading:

==========================
Reading Frames From A File
==========================

``rogue.utilities.fileio.StreamReader`` replays captured Rogue files as stream
frames. Frame metadata (channel, flags, error) is reconstructed and propagated
with each emitted frame.

``pyrogue.utilities.fileio.StreamReader`` wraps that replay source in a
tree-managed ``Device``. The lower-level reader is the simpler fit for scripts
and standalone stream graphs. The PyRogue wrapper is the better fit when replay
should start from a ``Root`` tree or client GUI.

Frames can be read in a streaming fashion using ``StreamReader``. Each data
record is emitted as a Rogue ``Frame`` with payload and metadata preserved from
the original file capture. If multiple channels were used during writing, the
replayed frames retain those channel IDs. A stream filter stage can then route
replayed frames by channel as needed.

For file-format details consumed by the reader, see
:ref:`utilities_fileio_format`.

Core Reader Controls
====================

The core reader is shaped by a small set of methods:

- ``open(path)``: Opens an input file and starts background replay.
- ``closeWait()``: Blocks until replay finishes, then closes the reader.
- ``close()``: Stops replay immediately and closes the reader.

When the input name ends with ``.1``, the reader automatically attempts
``.2``, ``.3``, and so on as a split-file sequence.

Tree-Managed Reader Form
========================

``pyrogue.utilities.fileio.StreamReader`` is a Python ``Device`` wrapper around
the same replay utility.

At the wrapper layer, the relevant controls are:

- ``DataFile`` for the selected input file
- ``Open`` and ``Close`` commands
- ``isOpen`` for replay status

The lower-level Rogue utility also exposes ``closeWait()``. The PyRogue
wrapper does not add a corresponding wait command, so wrapper-level code
typically calls ``Open()`` and then polls ``isOpen`` when blocking behavior is
needed.

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

Python Direct-Utility Example
=============================

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

Python Tree-Managed Example
===========================

.. code-block:: python

   import pyrogue.utilities.fileio as puf

   # Add a tree-managed reader so file replay can be controlled by clients/GUI.
   fread = puf.StreamReader()
   root.add(fread)

   # Route replayed frames to a downstream stream consumer.
   fread >> receiver

   import time

   # Configure and run replay via Device variables/commands.
   fread.DataFile.set("myFile.dat.1")
   fread.Open()

   # Wait for replay to finish when script-style blocking behavior is needed.
   while fread.isOpen.get():
      time.sleep(0.1)

This wrapper is a natural partner for tree-facing stream sinks such as
``pyrogue.DataReceiver`` subclasses: the reader provides the replay source,
and the downstream device decodes or publishes the replayed frames.

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
- Python: :doc:`/api/python/pyrogue/utilities/fileio/streamreader`
