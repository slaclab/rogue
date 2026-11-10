.. _utilities_fileio_python_reader:

==================
Python File Reader
==================

``pyrogue.utilities.fileio.FileReader`` provides direct Python iteration over
Rogue file records without constructing a live stream topology.

The Rogue ``FileReader`` class is a lightweight Python class that can be used
on its own with minimal dependencies. It supports processing stored data
frame-by-frame, and supports automatic extraction of configuration/status data
that may exist in a specified ``configChan`` channel. The ``files`` parameter
can be a single file or a list of segmented data files.

It is useful for offline analysis, quick inspection scripts, and extracting
metadata/configuration records from captured files.

Basic Usage
===========

.. code-block:: python

   from pyrogue.utilities.fileio import FileReader

   with FileReader(files="mydata.dat", configChan=1) as fd:
      for header, data in fd.records():
         print(f"Record {fd.currCount}/{fd.totCount}")
         print(f"  Channel = {header.channel}")
         print(f"  Size    = {header.size}")
         print(f"  Flags   = {header.flags:#x}")
         print(f"  Error   = {header.error:#x}")

         # data is a numpy array view of payload bytes
         print(f"  First byte = {data[0]:#x}")

      # Configuration/status state decoded from config channel frames
      print(fd.configDict.get("root.Time"))

Batcher-Aware Usage
===================

For files containing batcher-formatted records, enable ``batched=True``.
This mode is used when a single Rogue file record contains one or more
sub-records packed with Batcher protocol headers. In that case, the iterator
returns ``(header, batchHeader, data)`` for each unpacked sub-record so you can
analyze per-subframe metadata (for example ``tdest`` and user fields) instead
of treating the payload as one opaque byte block.

For protocol background, see :doc:`/built_in_modules/protocols/batcher/index`.

.. code-block:: python

   from pyrogue.utilities.fileio import FileReader

   with FileReader(files="mydata.dat", configChan=1, batched=True) as fd:
      for header, bheader, data in fd.records():
         print(f"Channel = {header.channel}, RecordBytes = {header.size}")
         print(f"BatchBytes = {bheader.size}, TDest = {bheader.tdest:#x}")

Behavior Notes
==============

- ``files`` may be a single file path or a list of file paths.
- ``configChan=None`` disables YAML config/status extraction.
- ``records()`` yields NumPy arrays for payload bytes.

Logging
=======

``FileReader`` uses Python logging, not Rogue C++ logging.

- Default logger name: ``pyrogue.FileReader``
- Logging API:
  ``pyrogue.setLogLevel('pyrogue.FileReader', 'DEBUG')``

If you pass a custom ``log=...`` object into ``FileReader``, that logger is
used instead of the default.

API Reference
=============

- Python:
  :doc:`/api/python/pyrogue/utilities/fileio/filereader`
  :doc:`/api/python/pyrogue/utilities/fileio/rogueheader`
