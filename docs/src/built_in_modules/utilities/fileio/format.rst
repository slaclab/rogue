.. _utilities_fileio_format:

======================
Rogue File Data Format
======================

The default on-disk record format used by :ref:`utilities_fileio_writer` and
consumed by :ref:`utilities_fileio_reader` is documented here.

Default Framed Mode
===================

In default mode (``raw`` disabled), each frame is written as one record:

.. code-block:: text

   record := headerA (4 bytes) + headerB (4 bytes) + payload (N bytes)

Both headers are 32-bit little-endian words.

Record Layout Diagram
=====================

Byte-level layout of one record on disk:

.. code-block:: text

   Offset  Size  Field
   ------  ----  --------------------------------------------
   0x00    4     headerA (uint32, little-endian)
   0x04    4     headerB (uint32, little-endian)
   0x08    N     payload bytes (exact frame payload)

Visualized as contiguous bytes:

.. code-block:: text

   +--------------------+--------------------+------------------------...------+
   | headerA[31:0] LE   | headerB[31:0] LE   | payload[0] ... payload[N-1]    |
   +--------------------+--------------------+------------------------...------+

Header field layout:

.. code-block:: c

      headerA:
          31:0  = (payload_bytes + 4)
                  // payload size plus the 4-byte headerB word

      headerB:
         31:24  = Channel ID passed to writeFile(channel, frame)
         23:16  = Frame error field (frame->getError())
          15:0  = Lower 16 bits of frame flags (frame->getFlags())

Bit-level view of ``headerB``:

.. code-block:: text

   31            24 23            16 15                             0
   +----------------+----------------+-------------------------------+
   |   Channel ID   |  Frame Error   |      Frame Flags[15:0]       |
   +----------------+----------------+-------------------------------+

Concrete example
================

If a frame has:

- Payload length = ``0x20`` bytes
- Channel = ``0x03``
- Error = ``0x00``
- Flags (low 16) = ``0x00A5``

Then:

- ``headerA = payload + 4 = 0x00000024``
- ``headerB = 0x030000A5``

On disk (little-endian bytes):

.. code-block:: text

   headerA: 24 00 00 00
   headerB: A5 00 00 03
   payload: <32 payload bytes follow>

Notes:

- Payload bytes are written exactly as they appear in the source frame buffers.
- The lower 16 bits of ``Frame.flags`` are persisted in the file.

Metadata Semantics
==================

``Frame.flags`` is a 16-bit metadata field. In many AXI-Stream/SSI flows, it
is used to carry TUSER sideband information:

- Bits ``[7:0]`` often represent first-tuser (SOF-side metadata)
- Bits ``[15:8]`` often represent last-tuser (EOF-side metadata)

The exact interpretation is protocol-dependent. StreamWriter stores this value
without modification so downstream software can decode it in the correct
protocol context.

``Frame.error`` is an 8-bit status field stored in ``headerB[23:16]``. Rogue
typically treats non-zero values as errored frames, but specific bit meanings
or enumerations are producer/protocol specific.
