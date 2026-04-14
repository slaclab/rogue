.. _utilities_fileio_reading:

==========================
Reading Frames From A File
==========================

For replay workflows that should be controlled from a PyRogue tree, PyRogue
provides ``pyrogue.utilities.fileio.StreamReader``. It wraps the lower-level
``rogue.utilities.fileio.StreamReader`` and exposes file selection plus open
and close commands through a small tree-visible ``Device``.

The underlying ``rogue.utilities.fileio.StreamReader`` reconstructs captured
Rogue records as live ``Frame`` traffic. Payload bytes, channel IDs, flags, and
error state are restored from the file and propagated downstream as replayed
frames.

Frames can be read in a streaming fashion using ``StreamReader``. Each data
record is emitted as a Rogue ``Frame`` with payload and metadata preserved from
the original file capture. If multiple channels were used during writing, the
replayed frames retain those channel IDs. A stream filter stage can then route
replayed frames by channel as needed.

For file-format details consumed by the reader, see
:ref:`utilities_fileio_format`.

When To Use Each Form
=====================

Use the wrapper when replay should be started from a ``Root`` tree, a GUI, or
remote client code. Use the direct Rogue reader when a standalone script just
needs a file-to-stream replay source.

Common Controls
===============

At the wrapper layer, most workflows only need:

- ``DataFile``
  Input filename exposed as a tree variable.
- ``Open``
  Starts replay.
- ``Close``
  Stops replay.
- ``isOpen``
  Reports whether replay is still active.

At the direct utility layer, the main controls are:

- ``open(path)``
- ``closeWait()``
- ``close()``

When the input name ends with ``.1``, the reader automatically attempts
``.2``, ``.3``, and so on as a split-file sequence.

Tree-Managed Reader Form
========================

``pyrogue.utilities.fileio.StreamReader`` is intentionally thinner than the
writer wrapper. It adds the file-selection variables and commands, but it does
not expose a tree-visible ``closeWait()`` equivalent.

That means wrapper-level code usually calls ``Open()`` and then polls
``isOpen`` when blocking behavior is needed. If a script wants direct blocking
control, the lower-level ``rogue.utilities.fileio.StreamReader`` remains the
simpler form.

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
