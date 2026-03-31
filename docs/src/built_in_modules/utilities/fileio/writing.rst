.. _utilities_fileio_writing:

========================
Writing Frames To A File
========================

For file capture that should be controlled from a PyRogue tree, PyRogue
provides ``pyrogue.utilities.fileio.StreamWriter``. It wraps
``rogue.utilities.fileio.StreamWriter`` and exposes the usual file controls
through :py:class:`~pyrogue.DataWriter`.

The underlying ``rogue.utilities.fileio.StreamWriter`` is still the object that
does the capture work. It receives Rogue ``Frame`` traffic on one or more input
channels and writes those frames in the standard Rogue file format, preserving
payload bytes plus frame metadata.

For the on-disk format details (header words, channel/flags/error encoding,
raw mode, and split-file behavior), see :ref:`utilities_fileio_format`.

When To Use Each Form
=====================

Use the PyRogue wrapper when operators or client code should be able to select
the output file, open and close runs, and watch file counters through the tree.
That is the pattern used in larger acquisition roots, where the writer becomes
part of the operator-facing control surface.

Use the direct Rogue writer when a script already owns the stream graph and
just needs a sink that writes files. That form is smaller and avoids the tree
layer entirely.

Common Controls
===============

At the wrapper level, most setups are shaped by a small set of controls:

- ``DataFile``
  Output file selected through the inherited ``pyrogue.DataWriter`` interface.
- ``BufferSize``
  Staging buffer size before writes are flushed to the OS.
- ``MaxFileSize``
  Non-zero enables split-file capture.
- ``configStream``
  Optional mapping of channel index to a stream source that emits YAML or
  status snapshots at file open and close.
- ``rawMode``
  When ``True``, write payload bytes only instead of the normal Rogue framed
  record format.

The direct writer has the matching lower-level methods:

- ``setBufferSize(bytes)``
- ``setMaxSize(bytes)``
- ``setDropErrors(bool)``
- ``getChannel(index)``
- ``open(path)``
- ``close()``

Channel Behavior
================

``StreamWriter`` supports multiple incoming stream channels. That detail is
important because capture files often mix event data, metadata, debug streams,
or multiple firmware virtual channels in one recording.

``getChannel(index)`` returns the sink for one capture path, but channel ``0``
has a special meaning. Data written through ``getChannel(0)`` preserves the
incoming frame's own channel metadata. Data written through ``getChannel(N)``
with ``N > 0`` is forced to file channel ``N`` regardless of the frame's
original channel field. That pattern is commonly used when a tree routes
distinct sources into fixed file channels.

Tree-Managed Writer Form
========================

The wrapper inherits the standard file-control surface from
:py:class:`~pyrogue.DataWriter`, then adds the file I/O-specific behavior from
the underlying Rogue writer.

In practice, the wrapper is usually configured around ``configStream``,
``rawMode``, and the inherited ``DataWriter`` controls such as ``DataFile``,
``BufferSize``, and ``MaxFileSize``.

In many systems, ``configStream`` is mapped to a reserved channel such as
``255`` so metadata stays separate from event/data channels.

Opening the wrapper does two things: it opens the file, then emits any
configured YAML or status streams into their assigned channels. Closing does
the same status dump again before the underlying writer shuts down. That is why
the wrapper is a better fit when the file should carry both event traffic and
the configuration context that surrounded the run.

Logging
=======

The underlying C++ ``StreamWriter`` uses Rogue C++ logging.

- Logger name: ``pyrogue.fileio.StreamWriter``
- Unified Logging API:
  ``pyrogue.setLogLevel('pyrogue.fileio.StreamWriter', 'DEBUG')``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.fileio.StreamWriter', rogue.Logging.Debug)``
- Typical messages: file open/close flow, split-file rollover, and write-path
  operational diagnostics

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
