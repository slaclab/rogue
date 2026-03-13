.. _utilities_compression_compression:

==================
Compressing Frames
==================

For compressing stream payloads in-line, Rogue provides
``rogue.utilities.StreamZip``. It consumes ordinary Rogue frames, compresses
the payload bytes with bzip2, and forwards a new frame downstream while
preserving frame metadata.

Use ``StreamZip`` when the next stage in the graph expects compressed payloads,
such as a file writer or a remote receiver that will later use
``StreamUnZip``.

Compression Pipeline
====================

A common compression chain looks like this:

- ``Prbs`` generates deterministic test payloads.
- ``StreamZip`` compresses each frame payload.
- ``StreamWriter`` records the compressed frames for later replay or analysis.

The same pattern appears in ``tests/test_file.py``.

Python Example
==============

.. code-block:: python

   import rogue.utilities as ru
   import rogue.utilities.fileio as ruf

   # Capture compressed output to file.
   writer = ruf.StreamWriter()
   writer.setBufferSize(1000)
   writer.setMaxSize(1_000_000)

   # Source generator and compression stage.
   prbs = ru.Prbs()
   comp = ru.StreamZip()

   # Pipeline: PRBS source -> compressor -> file sink.
   prbs >> comp >> writer.getChannel(0)

   # Generate and capture compressed traffic.
   writer.open('test.dat')
   for _ in range(1000):
       prbs.genFrame(1000)
   writer.close()

C++ Example
===========

.. code-block:: cpp

   #include <rogue/utilities/Prbs.h>
   #include <rogue/utilities/StreamZip.h>
   #include <rogue/utilities/fileio/StreamWriter.h>
   #include <rogue/utilities/fileio/StreamWriterChannel.h>

   namespace ru  = rogue::utilities;
   namespace ruf = rogue::utilities::fileio;

   int main() {
       // Capture compressed output to file.
       auto writer = ruf::StreamWriter::create();
       writer->setBufferSize(10000);
       writer->setMaxSize(100000000);
       writer->setDropErrors(true);

       // Source generator and compression stage.
       auto prbs = ru::Prbs::create();
       auto comp = ru::StreamZip::create();

       // Pipeline: PRBS source -> compressor -> file sink.
       *prbs >> comp >> writer->getChannel(0);

       // Generate and capture compressed traffic.
       writer->open("test.dat");
       for (int i = 0; i < 1000; ++i) prbs->genFrame(1000);
       writer->close();
       return 0;
   }

Threading And Lifecycle
=======================

``StreamZip`` does not create an internal worker thread. Compression runs
inside ``acceptFrame()`` in the caller thread, and the implementation locks the
input frame while reading payload bytes.

Operational Notes
=================

- Output frame allocation starts from the input payload size and grows if
  needed.
- Frame metadata is preserved across the compression step.
- Compression is easiest to reason about when the corresponding replay or
  receive path clearly includes :doc:`decompress`.

Related Topics
==============

- :doc:`decompress`
- :doc:`/built_in_modules/utilities/fileio/writing`

API Reference
=============

- Python: :doc:`/api/python/rogue/utilities/compression/streamzip`
- C++: :doc:`/api/cpp/utilities/compression/zip`
