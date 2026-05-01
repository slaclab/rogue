.. _utilities_hls_reg_interf_parser:

==============================
HLS Register Interface Parser
==============================

The module :py:mod:`~pyrogue.utilities.hls._RegInterfParser` parses HLS-generated
register header macros and generates a starter Rogue application file
(``application.py``) containing `RemoteVariable`, `RemoteCommand`, or
`MemoryDevice` definitions.

Why This Utility Exists
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

Typical Workflow
================

1. Build/export your HLS project artifacts.
2. Provide the generated archive to this utility.
3. Select output type (`RemoteVariable`, `RemoteCommand`, or `MemoryDevice`).
4. Review/edit the generated ``application.py`` and integrate it into your
   project's Rogue tree.

Supported Macro Patterns
========================

The parser groups related register macros by common name stems and key suffixes:

- ``ADDR``
- ``BASE`` / ``HIGH``
- ``BITS`` / ``WIDTH``
- ``DEPTH``

From these macros, it derives name, address offset, width/depth, and emits
appropriate constructor arguments in the generated Python code.

Parser Workflow
===============

``run()`` is the CLI entry point. It parses the command-line options that
select output mode, sets parser state for the selected target object type, and
then calls ``parse()`` followed by ``write()``.

``parse()`` prompts for the zip-file location, validates and extracts the
archive, locates a ``*_hw.h`` header, collects and groups ``#define`` macros,
enforces the current 64-bit width limit, and returns normalized parameter
records for the selected output mode.

``write(parameters)`` generates ``application.py`` from those records. It
writes an ``Application(pr.Device)`` class skeleton, emits one definition block
per parsed record, and leaves placeholders for later user customization in
``initialize()``.

Notes And Limitations
=====================

- The utility creates a starting point; manual cleanup/refinement is expected.
- Macro naming conventions in HLS output drive parsing quality.
- Complex register semantics (arrays, packed bitfields, side effects) may need
  hand-editing after generation.

Related Topics
==============

- Building the resulting tree model: :doc:`/pyrogue_tree/index`
- Device composition patterns: :doc:`/pyrogue_tree/core/device`
