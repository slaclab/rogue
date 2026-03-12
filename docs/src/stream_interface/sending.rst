.. _interfaces_stream_sending:
.. _stream_interface_sending:

==============
Sending Frames
==============

Custom transmitters are typically implemented by subclassing
:ref:`interfaces_stream_master`.

You usually write a custom stream ``Master`` when an application needs to originate
data rather than just route or transform it. Common cases include packetizing a
software data source, generating simulated or diagnostic traffic, wrapping a
piece of hardware that produces bytes on demand, or translating some other data
model into Rogue ``Frame`` objects. The ``Master`` owns the act of creating a ``Frame`` and
handing it to the downstream stream topology.

At a high level, sending a ``Frame`` always follows the same pattern:

1. Request a ``Frame`` from the primary ``Slave``.
2. Fill payload and metadata.
3. Send the ``Frame`` to connected ``Slave`` objects.

``Frame`` allocation is driven by the downstream primary ``Slave``. In most
cases you should request the ``Frame`` with ``zeroCopyEn=True`` and let that
``Slave`` decide whether to supply zero-copy buffers. If the same ``Frame``
object must be reused or resent, request it with ``zeroCopyEn=False`` because
zero-copy ``Frame`` objects are often consumed or emptied by the primary path
once sent.

Python and C++ subclasses are interchangeable at runtime: a Python ``Master``
can send into C++ ``Slave`` objects, and a C++ ``Master`` can send into Python
``Slave`` objects. That makes
it practical to prototype the control flow in Python first, then move only the
performance-critical transmitter into C++.

Python Master Subclass
======================

.. code-block:: python

   import numpy as np
   import rogue.interfaces.stream as ris

   class MyCustomMaster(ris.Master):

       def __init__(self):
           super().__init__()

       def send_bytes(self, payload: bytes, chan: int = 0):
           # Request a ``Frame`` from the primary ``Slave``. The requested size is the
           # total capacity we need. Passing True allows the downstream path to
           # choose zero-copy buffers when that is beneficial.
           frame = self._reqFrame(len(payload), True)
           with frame.lock():
               # Write the payload starting at offset 0. In Python this
               # automatically extends the valid ``Frame`` payload length.
               frame.write(payload)

               # Attach metadata before releasing the ``Frame`` downstream.
               frame.setChannel(chan)

           # After _sendFrame() returns, the connected ``Slave`` objects have
           # accepted the ``Frame`` and a zero-copy implementation may have
           # consumed it.
           self._sendFrame(frame)

       def send_numpy(self, arr: np.ndarray, chan: int = 0):
           arr = np.asarray(arr, dtype=np.uint8)
           frame = self._reqFrame(arr.nbytes, True)
           with frame.lock():
               # putNumpy() is the safer NumPy-specific path because it handles
               # strided or non-contiguous arrays correctly.
               frame.putNumpy(arr)
               frame.setChannel(chan)
           self._sendFrame(frame)

The Python transmit path is compact because the binding hides a few mechanical
steps. ``frame.write()`` accepts ordinary Python buffer objects such as
``bytes``, ``bytearray``, and contiguous NumPy arrays, and it automatically
advances the ``Frame`` payload to the highest byte written. ``frame.putNumpy()`` is
more explicit when the source is a NumPy array and is usually the better choice
when the array may be strided or non-contiguous. If a ``Frame`` must be reused,
request it with ``zeroCopyEn=False`` so that the downstream path does not hand
back a ``Frame`` whose buffers will be consumed on send. For shared ``Frame``
semantics and metadata behavior, see :doc:`/stream_interface/frame_model`.

For many applications, this Python pattern is enough. It is easy to read, easy
to test, and integrates naturally with Python-side orchestration. When the data
rate is moderate or ``Frame`` construction is driven by higher-level application
logic, the convenience usually outweighs the extra overhead.

C++ Master Subclass
===================

The C++ flow follows the same overall pattern, but payload access is more
explicit. You usually declare the valid payload length with ``setPayload()``,
then fill the ``Frame`` through a ``FrameIterator``. That is the normal Rogue style
because a ``Frame`` is a logical byte stream, not necessarily a single contiguous
block of memory.

This is usually the right choice when the transmitter is performance-sensitive,
when it is already implemented in C++, or when it needs tight control over the
layout and copy path used to populate the ``Frame``.

.. code-block:: cpp

   #include <algorithm>
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
         ris::FramePtr frame;
         ris::FrameIterator it;
         uint32_t x;

         // Request a ``Frame`` large enough to hold the outgoing payload.
         frame = reqFrame(size, true);
         auto lock = frame->lock();

         // In C++ the ``Frame`` payload size is generally declared explicitly.
         frame->setPayload(size);
         frame->setChannel(chan);

         // Get an iterator to the first byte in the ``Frame``.
         it = frame->begin();

         // Direct iterator writes are convenient for a few fixed fields.
         for (x = 0; x < 4 && x < size; x++) {
            *it = static_cast<uint8_t>(x);
            ++it;
         }

         // std::copy is the safest general-purpose bulk write because the
         // iterator handles ``Frame`` objects backed by multiple buffers.
         if (size > 4) {
            it = std::copy(data + 4, data + size, it);
         }

         // After sendFrame(), the downstream path owns the ``Frame`` contents.
         sendFrame(frame);
      }
   };

Transmit Frame Layout
===============================

Common transmit-side ``Frame`` API patterns include metadata tagging and offset
layout writes.

In practice, many transmitters need more than "write bytes and send". They need
to prepend a header, place payload data at a known offset, and annotate the
``Frame`` so downstream code can route or interpret it correctly. The examples below
show that more realistic pattern in both languages.

Python Header And Payload Example
----------------------------------------

.. code-block:: python

   import numpy as np

   header = bytes([0xA5, 0x5A, 0x01, 0x00])
   payload = np.arange(256, dtype=np.uint8)

   frame = self._reqFrame(len(header) + payload.nbytes, True)
   with frame.lock():
       # The header is written at offset 0 because write() defaults to the
       # beginning of the ``Frame``.
       frame.write(header)

       # The payload starts immediately after the header by using an explicit
       # offset.
       frame.putNumpy(payload, len(header))

       # Metadata can be used downstream for routing or packet interpretation.
       frame.setChannel(2)
       frame.setFlags(0)
       frame.setFirstUser(0x11)
       frame.setLastUser(0x22)

       # getSize() is total capacity, while getPayload() is the number of valid
       # bytes currently defined in the ``Frame``.
       assert frame.getPayload() == len(header) + payload.nbytes
       assert frame.getAvailable() == frame.getSize() - frame.getPayload()

   self._sendFrame(frame)

C++ Header And Payload Example
-------------------------------------

.. code-block:: cpp

   #include <array>
   #include <vector>
   #include "rogue/interfaces/stream/Frame.h"
   #include "rogue/interfaces/stream/FrameIterator.h"

   namespace ris = rogue::interfaces::stream;

   void MyCustomMaster::sendPacketWithLayout() {
      std::array<uint8_t, 4> header = {0xA5, 0x5A, 0x01, 0x00};
      std::vector<uint8_t> payload(256);
      for (size_t i = 0; i < payload.size(); ++i) payload[i] = static_cast<uint8_t>(i);

      auto frame = reqFrame(static_cast<uint32_t>(header.size() + payload.size()), true);
      auto lock  = frame->lock();

      // Declare how many bytes will be valid once construction finishes.
      frame->setPayload(static_cast<uint32_t>(header.size() + payload.size()));

      // Write the fixed-size header at the front of the ``Frame``.
      auto itHdr = frame->begin();
      ris::toFrame(itHdr, static_cast<uint32_t>(header.size()), header.data());

      // Then write the payload beginning immediately after the header.
      auto itPay = frame->begin() + static_cast<int32_t>(header.size());
      ris::toFrame(itPay, static_cast<uint32_t>(payload.size()), payload.data());

      frame->setChannel(2);
      frame->setFlags(0);
      frame->setFirstUser(0x11);
      frame->setLastUser(0x22);

      // Release the completed ``Frame`` to connected ``Slave`` objects.
      sendFrame(frame);
   }



Efficient C++ Payload Writes
===============================

Iterator use is worth spelling out in more detail because it explains why the
Rogue stream API looks the way it does. A ``Frame`` represents a logical byte
stream, but the bytes do not have to live in one contiguous block of memory.
The underlying storage may be made of multiple ``Buffer`` objects, and that is
often intentional. For example, a transport or allocator may build a large
``Frame`` from a sequence of packet-sized segments. A ``FrameIterator`` hides those
layout details and lets you walk the frame as if it were contiguous.

That is why ``std::copy`` and the helper functions such as ``toFrame()`` are
the safest general-purpose transmit tools. They keep working when the ``Frame`` is
split across multiple buffers, and they let the transmitter remain agnostic to
how the downstream path allocated the storage. In most code this is the right
tradeoff: correctness, clarity, and layout independence matter more than the
small overhead of iterator bookkeeping.

There are cases where that overhead matters. If profiling shows that transmit
side copies are a real bottleneck, you can drop down to contiguous-buffer
copies one segment at a time. The iterator provides two pieces of information
for that: ``remBuffer()`` reports how many bytes remain in the current
contiguous segment, and ``ptr()`` returns a direct pointer into that segment.
That leads to a pattern like this:

.. code-block:: cpp

   uint32_t count;
   uint8_t* src = data;

   frame = reqFrame(100, true);
   frame->setPayload(100);

   it = frame->begin();

   while (it != frame->end()) {
      // Bytes left in the current contiguous region.
      count = it.remBuffer();

      // Direct copy into this region.
      std::memcpy(it.ptr(), src, count);

      src += count;
      it += count;
   }

This approach is more verbose than ``std::copy`` because you are now managing
the segment boundaries yourself, but it avoids per-byte iterator work inside
the copy loop. It is a useful optimization when the ``Frame`` layout is segmented
and you still want efficient bulk transfer.

For structured fields at known offsets, ``toFrame()`` is often the clearest
option because it preserves the iterator semantics while handling the byte count
and iterator advance for you.

.. code-block:: cpp

   uint64_t data64;
   uint32_t data32;
   uint8_t  data8;

   frame->setPayload(13);
   it = frame->begin();

   // Write 64 bits and advance 8 bytes.
   ris::toFrame(it, 8, &data64);

   // Then 32 bits and advance 4 bytes.
   ris::toFrame(it, 4, &data32);

   // Then the final byte.
   ris::toFrame(it, 1, &data8);

If you need high-performance element-level access, use
:ref:`interfaces_stream_frame_accessor` after verifying that the target range
lives in a single contiguous buffer. ``ensureSingleBuffer(frame, true)`` can
flatten a ``Frame`` into one buffer when necessary, but that should be a deliberate
decision because flattening may undo a segmentation strategy chosen by the
upstream allocator.

Taken together, these access patterns form a progression. Start with iterator
based code, because it is robust and matches Rogue's ``Frame`` model. Move to
segment-by-segment contiguous copies only when measurements show the iterator
path is too expensive. Use ``FrameAccessor`` only for the narrow cases where
you truly need typed array-style access and can guarantee contiguous storage.

What To Explore Next
====================

- Frame semantics and metadata behavior: :doc:`/stream_interface/frame_model`
- Receive-side access patterns: :doc:`/stream_interface/receiving`
- Built-in module insertion points: :doc:`/stream_interface/built_in_modules`
- Stream connection topologies: :doc:`/stream_interface/connecting`

Related Topics
==============

- Building custom C++ extensions: :doc:`/custom_module/index`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/master`
  - :doc:`/api/python/rogue/interfaces/stream/frame`

- C++:

  - :doc:`/api/cpp/interfaces/stream/master`
  - :doc:`/api/cpp/interfaces/stream/helpers`
  - :doc:`/api/cpp/interfaces/stream/frameAccessor`
  - :doc:`/api/cpp/interfaces/stream/frame`
