.. _utilities_compression_decompression:

====================
Decompressing Frames
====================

For restoring payload bytes from a compressed Rogue stream, Rogue provides
``rogue.utilities.StreamUnZip``. It consumes frames produced by
``StreamZip`` or another compatible bzip2-compressed source, inflates the
payload, and forwards a new frame downstream while preserving frame metadata.

Use ``StreamUnZip`` on the receive or replay side of a pipeline that previously
inserted ``StreamZip``.

Decompression Pipeline
======================

A common decompression chain reverses the compression workflow:

- ``StreamReader`` replays compressed frames from disk.
- ``StreamUnZip`` inflates each payload.
- ``Prbs`` verifies integrity and reports receive and error counts.

Python Example
==============

.. code-block:: python

   import rogue.utilities as ru
   import rogue.utilities.fileio as ruf

   # Replay compressed frames from file.
   reader = ruf.StreamReader()

   # Decompression stage and downstream checker.
   decomp = ru.StreamUnZip()
   prbs = ru.Prbs()

   # Pipeline: file replay -> decompressor -> PRBS checker.
   reader >> decomp >> prbs

   # Run replay and wait for completion.
   reader.open('myFile.dat.1')
   reader.closeWait()

   # Summarize checker statistics.
   print(f'Received {prbs.getRxCount()} frames')
   print(f'Received {prbs.getRxErrors()} errors')

C++ Example
===========

.. code-block:: cpp

   #include <rogue/utilities/fileio/StreamReader.h>
   #include <rogue/utilities/Prbs.h>
   #include <rogue/utilities/StreamUnZip.h>

   namespace ru  = rogue::utilities;
   namespace ruf = rogue::utilities::fileio;

   int main() {
       // Replay source, decompressor, and checker endpoints.
       auto reader = ruf::StreamReader::create();
       auto decomp = ru::StreamUnZip::create();
       auto prbs   = ru::Prbs::create();

       // Pipeline: file replay -> decompressor -> PRBS checker.
       *reader >> decomp >> prbs;

       // Run replay and wait for completion.
       reader->open("myFile.dat.1");
       reader->closeWait();

       // Summarize checker statistics.
       printf("Received %u frames\n", prbs->getRxCount());
       printf("Received %u errors\n", prbs->getRxErrors());
       return 0;
   }

Threading And Lifecycle
=======================

``StreamUnZip`` does not create an internal worker thread. Decompression runs
inside ``acceptFrame()`` in the caller thread, and the implementation locks the
input frame while reading payload bytes.

Operational Notes
=================

- Output frame allocation starts from the compressed payload size and grows if
  needed.
- Frame metadata is preserved across the decompression step.
- The decompressor should match a stream path that actually contains compressed
  payloads.

Related Topics
==============

- :doc:`compress`
- :doc:`/built_in_modules/utilities/fileio/reading`

API Reference
=============

- Python: :doc:`/api/python/rogue/utilities/compression/streamunzip`
- C++: :doc:`/api/cpp/utilities/compression/unzip`
