.. _utilities_compression_compression:

==================
Compressing Frames
==================

``rogue.utilities.StreamZip`` compresses frame payload bytes in-line in a
stream pipeline while preserving frame metadata.

Method Overview
===============

The examples use a simple linear topology:

- ``Prbs`` generates deterministic test payloads.
- ``StreamZip`` compresses each frame payload.
- ``StreamWriter`` records compressed frames for replay/analysis.

Python Compression Pipeline
===========================

.. code-block:: python

   import rogue.utilities as ru
   import rogue.utilities.fileio as ruf

   # Capture compressed output to file.
   fwrite = ruf.StreamWriter()
   fwrite.setBufferSize(1000)
   fwrite.setMaxSize(1_000_000)

   # Source generator and compression stage.
   prbs = ru.Prbs()
   comp = ru.StreamZip()

   # Pipeline: PRBS source -> compressor -> file sink.
   prbs >> comp >> fwrite.getChannel(0)

   # Generate and capture compressed traffic.
   fwrite.open("test.dat")
   for _ in range(1000):
      prbs.genFrame(1000)
   fwrite.close()

C++ Compression Pipeline
========================

.. code-block:: cpp

   #include <rogue/utilities/Prbs.h>
   #include <rogue/utilities/StreamZip.h>
   #include <rogue/utilities/fileio/StreamWriter.h>
   #include <rogue/utilities/fileio/StreamWriterChannel.h>

   namespace ru  = rogue::utilities;
   namespace ruf = rogue::utilities::fileio;

   // Capture compressed output to file.
   auto fwrite = ruf::StreamWriter::create();
   fwrite->setBufferSize(10000);
   fwrite->setMaxSize(100000000);
   fwrite->setDropErrors(true);

   // Source generator and compression stage.
   auto prbs = ru::Prbs::create();
   auto comp = ru::StreamZip::create();

   // Pipeline: PRBS source -> compressor -> file sink.
   *prbs >> comp >> fwrite->getChannel(0);

   // Generate and capture compressed traffic.
   fwrite->open("test.dat");
   for (int i = 0; i < 1000; ++i) prbs->genFrame(1000);
   fwrite->close();

Related References
==================

- :doc:`/api/cpp/utilities/compression/zip`
- :doc:`decompress`
