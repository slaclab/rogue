.. _utilities_fileio_writing:

========================
Writing Frames To A File
========================

``rogue.utilities.fileio.StreamWriter`` captures incoming stream frames into a
Rogue file format that preserves payload bytes plus frame metadata.

``pyrogue.utilities.fileio.StreamWriter`` wraps that writer in a tree-managed
``Device`` by subclassing :py:class:`~pyrogue.DataWriter`. The lower-level
writer is the simpler fit for scripts and standalone stream graphs. The PyRogue
wrapper is the better fit when file capture should be started from a ``Root``
tree or a client GUI.

For the on-disk format details (header words, channel/flags/error encoding,
raw mode, and split-file behavior), see :ref:`utilities_fileio_format`.

Core Writer Controls
====================

The core writer is shaped by a small set of methods:

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

Tree-Managed Writer Form
========================

``pyrogue.utilities.fileio.StreamWriter`` is a Python ``Device`` wrapper around
the same writer backend.

The wrapper is usually configured around:

- ``configStream`` for channels that should emit YAML/config snapshots at file
  open and close
- ``rawMode`` when payload-only recording is desired
- the inherited ``DataWriter`` controls such as ``DataFile``, ``BufferSize``,
  and ``MaxFileSize``

In many systems, ``configStream`` is mapped to a reserved channel such as
``255`` so metadata stays separate from event/data channels.

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

Python Direct-Utility Example
=============================

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

Python Tree-Managed Example
===========================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.interfaces.stream as pis
   import pyrogue.utilities.fileio as puf
   import pyrogue.utilities.prbs as pup

   class MyRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           # Tree-managed writer with a reserved metadata channel.
           status_stream = pis.Variable(root=self)
           self.add(puf.StreamWriter(name='Writer', configStream={255: status_stream}))

           # Real stream source feeding capture channel 0.
           self.add(pup.PrbsTx(name='PrbsTx'))
           self.PrbsTx >> self.Writer.getChannel(0)

   root = MyRoot()

   # File control can be performed through Device variables/commands.
   root.Writer.DataFile.set("myFile.dat")
   root.Writer.Open()
   # ...
   root.Writer.Close()

Opening the file starts capture and emits any configured YAML/status streams.
Closing the file emits those streams again before the writer shuts down. That
pattern is useful because the file records both data traffic and the
configuration context that surrounded the run.

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
- Python: :doc:`/api/python/pyrogue/utilities/fileio/streamwriter`
