.. _utilities_fileio:

==================
File I/O Utilities
==================

The File I/O utilities provide a standard record format and stream endpoints
for writing and replaying frame data.

Rogue file operations are centered on frame capture and replay:

- ``StreamWriter`` captures stream traffic and writes framed records to disk.
- ``StreamReader`` replays those records back into stream pipelines.
- ``FileReader`` supports direct Python-side offline inspection/analysis.

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

Subtopic Guide
==============

- :doc:`format`: Defines the canonical Rogue on-disk record structure.
- :doc:`writing`: Covers capture paths, writer channels, and split-file
  operation.
- :doc:`reading`: Covers replay behavior and stream re-injection patterns.
- :doc:`python_reader`: Covers lightweight, non-stream Python analysis flows.
- :doc:`custom`: Covers subclassing ``StreamWriter`` for custom output formats.

.. toctree::
   :maxdepth: 1
   :caption: File I/O Utilities:

   format
   writing
   reading
   custom
   python_reader
