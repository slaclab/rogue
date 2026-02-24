.. _utilities_fileio_format:

======================
Rogue File Data Format
======================

This page documents the default on-disk record format used by
:ref:`utilities_fileio_writer` and consumed by :ref:`utilities_fileio_reader`.

Default Framed Mode
===================

In default mode (``raw`` disabled), each frame is written as one record:

.. code-block:: text

   record := headerA (4 bytes) + headerB (4 bytes) + payload (N bytes)

Both headers are 32-bit little-endian words.

Header field layout:

.. code-block:: c

      headerA:
          31:0  = (payload_bytes + 4)
                  // payload size plus the 4-byte headerB word

      headerB:
         31:24  = Channel ID passed to writeFile(channel, frame)
         23:16  = Frame error field (frame->getError())
          15:0  = Lower 16 bits of frame flags (frame->getFlags())

Notes:

- Payload bytes are written exactly as they appear in the source frame buffers.
- The lower 16 bits of ``Frame.flags`` are persisted in the file.

Metadata Semantics
==================

``Frame.flags`` is a 16-bit metadata field. In many AXI-Stream/SSI flows, it
is used to carry TUSER sideband information:

- bits ``[7:0]`` often represent first-tuser (SOF-side metadata)
- bits ``[15:8]`` often represent last-tuser (EOF-side metadata)

The exact interpretation is protocol-dependent. StreamWriter stores this value
without modification so downstream software can decode it in the correct
protocol context.

``Frame.error`` is an 8-bit status field stored in ``headerB[23:16]``. Rogue
typically treats non-zero values as errored frames, but specific bit meanings
or enumerations are producer/protocol specific.

