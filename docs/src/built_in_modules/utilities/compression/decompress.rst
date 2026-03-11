.. _utilities_compression_decompression:

====================
Decompressing Frames
====================

``rogue.utilities.StreamUnZip`` restores payload bytes from a compressed stream
produced by ``StreamZip``.

Method Overview
===============

The examples reverse the compression pipeline:

- ``StreamReader`` replays compressed frames from disk.
- ``StreamUnZip`` inflates each payload.
- ``Prbs`` verifies integrity and reports receive/error counts.

Python Decompression Pipeline
=============================

.. code-block:: python

   import rogue.utilities as ru
   import rogue.utilities.fileio as ruf

   # Replay compressed frames from file.
   fread = ruf.StreamReader()

   # Decompression stage and downstream checker.
   decomp = ru.StreamUnZip()
   prbs = ru.Prbs()

   # Pipeline: file replay -> decompressor -> PRBS checker.
   decomp << fread
   prbs << decomp

   # Run replay and wait for completion.
   fread.open("myFile.dat.1")
   fread.closeWait()

   # Summarize checker statistics.
   print(f"Received {prbs.getRxCount()} frames")
   print(f"Received {prbs.getRxErrors()} errors")

C++ Decompression Pipeline
==========================

.. code-block:: cpp

   #include <rogue/utilities/fileio/StreamReader.h>
   #include <rogue/utilities/Prbs.h>
   #include <rogue/utilities/StreamUnZip.h>

   namespace ru  = rogue::utilities;
   namespace ruf = rogue::utilities::fileio;

   // Replay source, decompressor, and checker endpoints.
   auto fread  = ruf::StreamReader::create();
   auto decomp = ru::StreamUnZip::create();
   auto prbs   = ru::Prbs::create();

   // Pipeline: file replay -> decompressor -> PRBS checker.
   *decomp << fread;
   *prbs << decomp;

   // Run replay and wait for completion.
   fread->open("myFile.dat.1");
   fread->closeWait();

   // Summarize checker statistics.
   printf("Received %u frames\n", prbs->getRxCount());
   printf("Received %u errors\n", prbs->getRxErrors());

Related Topics
==============

- :doc:`compress`

API Reference
=============

- Python: :doc:`/api/python/utilities_compression_streamunzip`
- C++: :doc:`/api/cpp/utilities/compression/unzip`
