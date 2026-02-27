.. _utilities_hls_reg_interf_parser:

==============================
HLS Register Interface Parser
==============================

The module :py:mod:`pyrogue.utilities.hls._RegInterfParser` parses HLS-generated
register header macros and generates a starter Rogue application file
(``application.py``) containing `RemoteVariable`, `RemoteCommand`, or
`MemoryDevice` definitions.

Why this utility exists
=======================

HLS flows often generate AXI addressable register maps described in ``*_hw.h``
header files. This utility helps convert those macro-based descriptions into a
Rogue tree scaffold so software can quickly mirror the hardware map.

CLI Usage
=========

Run the parser module with one output mode:

.. code-block:: bash

   python -m pyrogue.utilities.hls._RegInterfParser --remoteVariable
   python -m pyrogue.utilities.hls._RegInterfParser --remoteCommand
   python -m pyrogue.utilities.hls._RegInterfParser --memoryDevice

At runtime, the tool prompts for a zip file path. It extracts the archive,
searches for a ``*_hw.h`` file, parses ``#define`` macros, groups related macro
families, and writes ``application.py`` in the current directory.

Typical workflow
================

1. Build/export your HLS project artifacts.
2. Provide the generated archive to this utility.
3. Select output type (`RemoteVariable`, `RemoteCommand`, or `MemoryDevice`).
4. Review/edit the generated ``application.py`` and integrate it into your
   project's Rogue tree.

Supported macro patterns
========================

The parser groups related register macros by common name stems and key suffixes:

- ``ADDR``
- ``BASE`` / ``HIGH``
- ``BITS`` / ``WIDTH``
- ``DEPTH``

From these macros, it derives name, address offset, width/depth, and emits
appropriate constructor arguments in the generated Python code.

Function Reference
==================

``run()``
---------

Top-level CLI entry point.

- Parses command-line options to select output mode.
- Sets parser state for the selected target object type.
- Calls ``parse()`` then ``write()``.

``parse()``
-----------

Parses HLS register macros and returns normalized parameter records.

- Prompts for zip file location.
- Validates zip input and extracts archive contents.
- Locates ``*_hw.h``.
- Collects and groups ``#define`` macros.
- Enforces a max width constraint (currently 64 bits).
- Returns a list of namedtuple records matching selected output mode.

``write(parameters)``
---------------------

Generates ``application.py`` from parsed records.

- Writes an ``Application(pr.Device)`` class skeleton.
- Emits one definition block per parsed record:
  - ``pr.RemoteVariable(...)``
  - ``pr.RemoteCommand(...)``
  - ``pr.MemoryDevice(...)``
- Leaves placeholders for user customization in ``initialize()``.

Notes and limitations
=====================

- The utility creates a starting point; manual cleanup/refinement is expected.
- Macro naming conventions in HLS output drive parsing quality.
- Complex register semantics (arrays, packed bitfields, side effects) may need
  hand-editing after generation.

