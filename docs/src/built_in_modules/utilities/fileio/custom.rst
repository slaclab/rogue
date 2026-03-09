.. _utilities_fileio_custom:

==============
Custom Writers
==============

Rogue provides a standard ``StreamWriter`` for storing stream data in the
default Rogue file format. In some systems, a custom file format is required
for downstream DAQ or analysis tools.

In those cases, derive from ``rogue::utilities::fileio::StreamWriter`` and
override ``writeFile()``. This keeps core writer behavior (channel fan-in,
buffering, split-file rollover, and counters) while allowing custom payload
serialization.

Custom C++ StreamWriter Subclass
================================

.. code-block:: cpp

   #include <rogue/utilities/fileio/StreamWriter.h>
   #include <rogue/interfaces/stream/Frame.h>
   #include <rogue/GilRelease.h>

   class MyDataWriter : public rogue::utilities::fileio::StreamWriter {
   protected:
      void writeFile(uint8_t channel,
                     std::shared_ptr<rogue::interfaces::stream::Frame> frame) override {

         // Critical when called through Python bindings: release the GIL
         // before taking C++ locks or doing file work.
         rogue::GilRelease noGil;

         // Keep default rollover + buffering behavior.
         uint32_t payload = frame->getPayload();
         std::unique_lock<std::mutex> lock(mtx_);
         checkSize(payload);

         // Example custom header line.
         char hdr[128];
         int n = snprintf(hdr, sizeof(hdr), "CHAN=%u BYTES=%u\n", channel, payload);
         intWrite(hdr, static_cast<uint32_t>(n));

         // Serialize frame payload bytes in your custom format.
         auto it = frame->begin();
         for (uint32_t i = 0; i < payload; ++i, ++it) {
            char b[8];
            int m = snprintf(b, sizeof(b), "%02x", static_cast<uint8_t>(*it));
            intWrite(b, static_cast<uint32_t>(m));
         }
         intWrite(const_cast<char*>("\n"), 1);

         frameCount_++;
         cond_.notify_all();
      }
   };

PyRogue Wrapper Pattern
=======================

If your custom writer is exposed to Python bindings, pass it into
``pyrogue.utilities.fileio.StreamWriter(writer=...)`` so normal tree controls
(``DataFile``, ``Open``, ``Close``, size/bandwidth counters) remain available.

Once your custom writer is created, you may also want to use it in the Rogue
tree so files can be opened and written through the Rogue PyDM GUI. In that
flow, use the PyRogue ``StreamWriter`` wrapper with your custom writer module.

.. code-block:: python

   import pyrogue.utilities.fileio as puf

   # my_writer is a Python-exposed instance of your C++ subclass.
   fwrite = puf.StreamWriter(writer=my_writer)
   root.add(fwrite)

   streamA >> fwrite.getChannel(0)
   streamB >> fwrite.getChannel(1)

Related References
==================

- :doc:`/api/cpp/utilities/fileio/writer`
- :doc:`/api/python/utilities_fileio_streamwriter`
