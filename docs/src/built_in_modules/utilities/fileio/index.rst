.. _utilities_fileio:

==================
File I/O Utilities
==================

For recording Rogue stream traffic to disk and replaying it later, Rogue
provides a file I/O family that spans both tree-managed PyRogue wrappers and
direct ``rogue.utilities.fileio`` endpoints.

The family is organized around three related roles:

- ``pyrogue.utilities.fileio.StreamWriter`` and
  ``pyrogue.utilities.fileio.StreamReader``
  Tree-managed wrappers that expose file selection and open/close control
  through a PyRogue tree.
- ``rogue.utilities.fileio.StreamWriter`` and
  ``rogue.utilities.fileio.StreamReader``
  Direct stream endpoints for capture and replay in standalone graphs or
  scripts.
- ``pyrogue.utilities.fileio.FileReader``
  A Python-side offline reader for analysis workflows that do not need to
  reconstruct a live stream graph.

The on-disk record format is shared by the whole family. Header words, channel
IDs, flags, error fields, split-file handling, and raw-mode behavior all come
from that format definition, so it is worth reading :doc:`format` early.

C++ API details for file I/O utilities are documented in
:doc:`/api/cpp/utilities/fileio/index`.

Common workflows include:

- Capturing one or more stream channels to disk during integration and debug.
- Replaying captured files back into processing pipelines.
- Reading records directly in Python for offline analysis.
- Extending the base writer for custom DAQ output formats.

The direct Rogue utilities are the simpler fit when a script already owns the
stream graph and just needs capture or replay endpoints. The PyRogue wrappers
are the better fit when file control should appear through ``DataFile``,
``Open``, ``Close``, ``IsOpen``, and the rest of the tree-visible state
inherited from ``pyrogue.DataWriter`` or added by the wrapper ``Device``.

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


Subtopics
=========

- :doc:`format`: Defines the canonical Rogue on-disk record structure.
- :doc:`writing`: Starts from the common ``pyrogue.utilities.fileio.StreamWriter``
  wrapper, then explains the underlying ``rogue.utilities.fileio.StreamWriter``
  controls and channel model.
- :doc:`reading`: Starts from the tree-managed replay wrapper, then explains the
  direct ``rogue.utilities.fileio.StreamReader`` behavior.
- :doc:`python_reader`: Lightweight coverage for non-stream Python analysis flows.
- :doc:`custom`: Guidance for subclassing ``StreamWriter`` for custom output formats.

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
