.. _interfaces_stream_receiving:
.. _stream_interface_receiving:

================
Receiving Frames
================

Custom receivers are typically implemented by subclassing
:ref:`interfaces_stream_slave` and overriding ``acceptFrame`` (C++) or
``_acceptFrame`` (Python).

For frame semantics and API details, see :doc:`/stream_interface/frame_model`.

The common flow is:

1. Lock the frame.
2. Read payload bytes or extract a NumPy copy.
3. Extract metadata (channel/error/flags).
4. Process or route based on metadata.

Python slave subclass
=====================

.. code-block:: python

   import numpy as np
   import rogue.interfaces.stream as ris

   class MyCustomSlave(ris.Slave):

       def __init__(self):
           super().__init__()

       def _acceptFrame(self, frame):
           with frame.lock():
               chan = frame.getChannel()
               err = frame.getError()
               flags = frame.getFlags()
               fuser = frame.getFirstUser()
               luser = frame.getLastUser()

               # Copy payload bytes into a NumPy uint8 array
               data_np = frame.getNumpy()

           if err:
               print(f"drop: chan={chan}, err=0x{err:02x}, flags=0x{flags:04x}")
               return

           self.handle_numpy(data_np, chan, fuser, luser)

       def handle_numpy(self, data_np: np.ndarray, chan: int, fuser: int, luser: int):
           print(f"rx chan={chan}, bytes={data_np.size}, firstUser={fuser}, lastUser={luser}")

Notes:

- ``frame.read(buffer, offset=0)`` copies into any writable Python buffer.
- ``frame.getNumpy(offset=0, count=0)`` returns a copied ``np.uint8`` array.
- ``frame.getMemoryview()`` provides a Python memoryview over copied frame data.

C++ slave subclass
==================

.. code-block:: cpp

   #include <array>
   #include <vector>
   #include "rogue/interfaces/stream/Slave.h"
   #include "rogue/interfaces/stream/Frame.h"
   #include "rogue/interfaces/stream/FrameIterator.h"
   #include "rogue/interfaces/stream/FrameLock.h"

   namespace ris = rogue::interfaces::stream;

   class MyCustomSlave : public ris::Slave {
   public:
      using Ptr = std::shared_ptr<MyCustomSlave>;
      static Ptr create() { return std::make_shared<MyCustomSlave>(); }

      void acceptFrame(ris::FramePtr frame) override {
         auto lock = frame->lock();

         const uint32_t size = frame->getPayload();
         std::vector<uint8_t> data(size);

         auto it = frame->begin();
         ris::fromFrame(it, size, data.data());

         const uint8_t chan  = frame->getChannel();
         const uint8_t err   = frame->getError();
         const uint16_t flags = frame->getFlags();
         const uint8_t fuser = frame->getFirstUser();
         const uint8_t luser = frame->getLastUser();

         process(data.data(), size, chan, err, flags, fuser, luser);
      }

      void process(const uint8_t* data,
                   uint32_t size,
                   uint8_t chan,
                   uint8_t err,
                   uint16_t flags,
                   uint8_t fuser,
                   uint8_t luser) {
         // Application-specific processing
      }
   };

Frame API patterns for receive
==============================

Python example (offset + metadata extraction)
---------------------------------------------

.. code-block:: python

   # Inside _acceptFrame(self, frame)
   with frame.lock():
       chan = frame.getChannel()
       err = frame.getError()
       flags = frame.getFlags()

       # Extract 32-byte header and remainder payload as NumPy copies
       header = frame.getNumpy(0, 32)
       payload = frame.getNumpy(32)

       # Alternative bytearray path
       raw = bytearray(frame.getPayload())
       frame.read(raw)

   if err == 0 and chan == 2:
       self.process_payload(payload, flags)

C++ example (offset + metadata extraction)
------------------------------------------

.. code-block:: cpp

   // Inside acceptFrame(ris::FramePtr frame)
   auto lock = frame->lock();

   const uint32_t size = frame->getPayload();
   const uint8_t chan = frame->getChannel();
   const uint8_t err = frame->getError();
   const uint16_t flags = frame->getFlags();

   // Read 32-byte header
   std::array<uint8_t, 32> header{};
   auto itHdr = frame->begin();
   ris::fromFrame(itHdr, static_cast<uint32_t>(header.size()), header.data());

   // Read payload after header
   const uint32_t payloadSize = (size > header.size()) ? (size - static_cast<uint32_t>(header.size())) : 0;
   std::vector<uint8_t> payload(payloadSize);
   auto itPay = frame->begin() + static_cast<int32_t>(header.size());
   ris::fromFrame(itPay, payloadSize, payload.data());

   if (err == 0 && chan == 2) {
      processPayload(payload.data(), payloadSize, flags);
   }

Debug base slave
================

For bring-up, the base ``Slave`` can be attached as a monitor and configured
with ``setDebug(maxBytes, name)`` to print frame summaries and byte dumps.

See :doc:`/stream_interface/debugStreams`.

Logging
=======

Most custom receive code uses one of two logging patterns:

- Python subclasses usually use normal Python ``logging`` inside
  ``_acceptFrame()``.
- C++ subclasses usually create a Rogue logger with
  ``rogue::Logging::create(...)`` inside the receiver class.

If you want quick byte-dump logging without writing a custom receiver, attach a
base ``Slave`` and call ``setDebug(maxBytes, name)``. That helper creates a
Rogue C++ logger named ``pyrogue.<name>``. For example,
``dbg.setDebug(128, 'stream.rx.tap')`` emits through ``pyrogue.stream.rx.tap``.

What To Explore Next
====================

- Frame construction and transmit patterns: :doc:`/stream_interface/sending`
- Connection topologies: :doc:`/stream_interface/connecting`
- Stream debugging patterns: :doc:`/stream_interface/debugStreams`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream_slave`
  - :doc:`/api/python/rogue/interfaces/stream_frame`

- C++:

  - :doc:`/api/cpp/interfaces/stream/slave`
  - :doc:`/api/cpp/interfaces/stream/frame`
