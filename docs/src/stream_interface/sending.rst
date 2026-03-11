.. _interfaces_stream_sending:
.. _stream_interface_sending:

==============
Sending Frames
==============

Custom transmitters are typically implemented by subclassing
:ref:`interfaces_stream_master`.

The common flow is:

1. Request a frame from the primary slave.
2. Fill payload and metadata.
3. Send the frame to connected slaves.

Python master subclass
======================

.. code-block:: python

   import numpy as np
   import rogue.interfaces.stream as ris

   class MyCustomMaster(ris.Master):

       def __init__(self):
           super().__init__()

       def send_bytes(self, payload: bytes, chan: int = 0):
           frame = self._reqFrame(len(payload), True)
           with frame.lock():
               frame.write(payload)
               frame.setChannel(chan)
           self._sendFrame(frame)

       def send_numpy(self, arr: np.ndarray, chan: int = 0):
           arr = np.asarray(arr, dtype=np.uint8)
           frame = self._reqFrame(arr.nbytes, True)
           with frame.lock():
               # NumPy-specific path; handles non-contiguous arrays.
               frame.putNumpy(arr)
               frame.setChannel(chan)
           self._sendFrame(frame)

Notes:

- ``_reqFrame(size, True)`` allows zero-copy allocation when supported.
- If a frame must be reused, request with ``zeroCopyEn=False``.
- ``frame.write(obj, offset)`` accepts Python buffer objects, including
  contiguous NumPy arrays.
- ``frame.putNumpy(arr, offset)`` is NumPy-specific and is safer for
  strided/non-contiguous arrays.
- For both ``write`` and ``putNumpy``, the ``offset`` argument defaults to
  ``0``.
- For shared frame semantics, see :doc:`/stream_interface/frame_model`.

C++ master subclass
===================

.. code-block:: cpp

   #include "rogue/interfaces/stream/Master.h"
   #include "rogue/interfaces/stream/Frame.h"
   #include "rogue/interfaces/stream/FrameIterator.h"
   #include "rogue/interfaces/stream/FrameLock.h"

   namespace ris = rogue::interfaces::stream;

   class MyCustomMaster : public ris::Master {
   public:
      using Ptr = std::shared_ptr<MyCustomMaster>;
      static Ptr create() { return std::make_shared<MyCustomMaster>(); }

      void sendPacket(const uint8_t* data, uint32_t size, uint8_t chan = 0) {
         auto frame = reqFrame(size, true);
         auto lock = frame->lock();

         frame->setPayload(size);
         auto it = frame->begin();
         ris::toFrame(it, size, const_cast<uint8_t*>(data));
         frame->setChannel(chan);

         sendFrame(frame);
      }
   };

Frame API patterns for transmit
===============================

Common transmit-side frame API patterns include metadata tagging and offset
layout writes.

Python example (header + payload layout)
----------------------------------------

.. code-block:: python

   import numpy as np

   header = bytes([0xA5, 0x5A, 0x01, 0x00])
   payload = np.arange(256, dtype=np.uint8)

   frame = self._reqFrame(len(header) + payload.nbytes, True)
   with frame.lock():
       # Offset defaults to 0 for header write
       frame.write(header)
       # Place payload after header
       frame.putNumpy(payload, len(header))

       frame.setChannel(2)
       frame.setFlags(0)
       frame.setFirstUser(0x11)
       frame.setLastUser(0x22)

       # Optional sanity checks while constructing
       # size is capacity, payload is bytes written/declared valid
       assert frame.getPayload() == len(header) + payload.nbytes
       assert frame.getAvailable() == frame.getSize() - frame.getPayload()

   self._sendFrame(frame)

C++ example (header + payload layout)
-------------------------------------

.. code-block:: cpp

   #include <array>
   #include <vector>
   #include "rogue/interfaces/stream/Frame.h"
   #include "rogue/interfaces/stream/FrameIterator.h"

   namespace ris = rogue::interfaces::stream;

   // Example method body for MyCustomMaster : public ris::Master
   void MyCustomMaster::sendPacketWithLayout() {
      std::array<uint8_t, 4> header = {0xA5, 0x5A, 0x01, 0x00};
      std::vector<uint8_t> payload(256);
      for (size_t i = 0; i < payload.size(); ++i) payload[i] = static_cast<uint8_t>(i);

      auto frame = reqFrame(static_cast<uint32_t>(header.size() + payload.size()), true);
      auto lock  = frame->lock();

      // Declare total valid payload before writing with iterators.
      frame->setPayload(static_cast<uint32_t>(header.size() + payload.size()));

      // Header at offset 0
      auto itHdr = frame->begin();
      ris::toFrame(itHdr, static_cast<uint32_t>(header.size()), header.data());

      // Payload at explicit offset = header.size()
      auto itPay = frame->begin() + static_cast<int32_t>(header.size());
      ris::toFrame(itPay, static_cast<uint32_t>(payload.size()), payload.data());

      frame->setChannel(2);
      frame->setFlags(0);
      frame->setFirstUser(0x11);
      frame->setLastUser(0x22);

      sendFrame(frame);
   }



Efficient payload writes in C++
===============================

- ``toFrame``/``fromFrame`` are safe across multi-buffer frames.
- For contiguous-only fast paths, use
  :ref:`interfaces_stream_frame_accessor` after verifying single-buffer layout.
- ``ensureSingleBuffer(frame, true)`` can copy into a one-buffer frame when
  needed.

See also:

- :doc:`/stream_interface/frame_model`
- :doc:`/stream_interface/receiving`
- :doc:`/api/cpp/interfaces/stream/helpers`
- :doc:`/api/cpp/interfaces/stream/frameAccessor`

What To Explore Next
====================

- Receive-side access patterns: :doc:`/stream_interface/receiving`
- Built-in module insertion points: :doc:`/stream_interface/built_in_modules`
- Stream connection topologies: :doc:`/stream_interface/connecting`

API Reference
=============

- Python:

  - :doc:`/api/python/interfaces_stream_master`
  - :doc:`/api/python/interfaces_stream_frame`

- C++:

  - :doc:`/api/cpp/interfaces/stream/master`
  - :doc:`/api/cpp/interfaces/stream/frame`
