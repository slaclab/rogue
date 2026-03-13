.. _utilities_fileio:

==================
File I/O Utilities
==================

The File I/O utilities provide a standard record format and stream endpoints
for writing and replaying frame data.

``rogue.utilities.fileio`` provides the core file writer and reader endpoints.
``pyrogue.utilities.fileio`` adds tree-managed ``Device`` wrappers around those
same endpoints when capture or replay should be controlled from a PyRogue tree.

Rogue file operations are centered on frame capture and replay:

- ``StreamWriter`` captures stream traffic and writes framed records to disk.
- ``StreamReader`` replays those records back into stream pipelines.
- ``FileReader`` supports direct Python-side offline inspection/analysis.
- ``pyrogue.utilities.fileio.StreamWriter`` and
  ``pyrogue.utilities.fileio.StreamReader`` wrap those endpoints as
  tree-managed devices.

The file format itself is foundational, because every writer/reader behavior
depends on how record headers, channel IDs, flags, and error fields are
encoded. Start with :doc:`format` before tuning capture/replay behavior.

C++ API details for file I/O utilities are documented in
:doc:`/api/cpp/utilities/fileio/index`.

Common workflows include:

- Capturing one or more stream channels to disk during integration and debug.
- Replaying captured files back into processing pipelines.
- Reading records directly in Python for offline analysis.
- Extending the base writer for custom DAQ output formats.

The direct Rogue utilities are the simpler fit for scripts and standalone
stream graphs. The PyRogue wrappers are the better fit when file control should
appear through ``DataFile``, ``Open``, ``Close``, and related tree state.

Logging
=======

The file I/O utilities use both Rogue C++ logging and Python logging,
depending on the object:

- ``rogue.utilities.fileio.StreamWriter`` uses Rogue C++ logging with logger
  name ``pyrogue.fileio.StreamWriter``.
- ``pyrogue.utilities.fileio.FileReader`` uses Python logging with logger
  name ``pyrogue.FileReader`` by default.

This means capture-path debugging and offline-analysis debugging use different
configuration APIs:

.. code-block:: python

   import logging
   import rogue

   rogue.Logging.setFilter('pyrogue.fileio.StreamWriter', rogue.Logging.Debug)
   logging.getLogger('pyrogue.FileReader').setLevel(logging.DEBUG)

Subtopic Guide
==============

- :doc:`format`: Defines the canonical Rogue on-disk record structure.
- :doc:`writing`: Covers capture paths, writer channels, and split-file
  operation.
- :doc:`reading`: Covers replay behavior and stream re-injection patterns.
- :doc:`python_reader`: Covers lightweight, non-stream Python analysis flows.
- :doc:`custom`: Covers subclassing ``StreamWriter`` for custom output formats.

API Reference
=============

- Python:

  - :doc:`/api/python/pyrogue/utilities/fileio/streamreader`
  - :doc:`/api/python/pyrogue/utilities/fileio/streamwriter`

- C++:

  - :doc:`/api/cpp/utilities/fileio/reader`
  - :doc:`/api/cpp/utilities/fileio/writer`

.. toctree::
   :maxdepth: 1
   :caption: File I/O Utilities:

   format
   writing
   reading
   custom
   python_reader
