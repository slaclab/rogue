.. _interfaces_stream_receiving:
.. _stream_interface_receiving:

================
Receiving Frames
================

Custom receivers are typically implemented by subclassing
:ref:`interfaces_stream_slave` and overriding ``acceptFrame`` in C++ or
``_acceptFrame`` in Python.

You usually write a custom stream ``Slave`` when an application needs to inspect,
decode, validate, log, or route incoming frame data. Common cases include
parsing headers from a hardware data source, unpacking payloads into a software
model, filtering traffic by channel or status bits, or attaching a temporary
diagnostic sink during bring-up. The ``Slave`` owns the act of accepting a ``Frame``
from the stream topology and turning it into whatever the application needs
next.

At a high level, receiving a ``Frame`` follows the same pattern in most designs:

1. Lock the ``Frame`` while reading its contents.
2. Read payload bytes or extract a copied view of the payload.
3. Inspect metadata such as channel, error, flags, and user fields.
4. Route, decode, log, or discard the ``Frame`` based on that information.

Python and C++ receiver subclasses can be mixed freely with ``Master`` objects written in
either language. That makes it practical to start with a lightweight Python
inspection ``Slave`` on an existing C++ stream path, then move the receive path into
C++ later if throughput or latency requires it.

For ``Frame`` semantics and API details, see :doc:`/stream_interface/frame_model`.

Python Slave Subclass
=====================

.. code-block:: python

   import numpy as np
   import rogue.interfaces.stream as ris

   class MyCustomSlave(ris.Slave):

       # Init method must call the parent class init
       def __init__(self):
           super().__init__()

       # Method which is called each time a ``Frame`` is received
       def _acceptFrame(self, frame):

           # Hold the ``Frame`` lock while reading payload and metadata.
           with frame.lock():
               chan = frame.getChannel()
               err = frame.getError()
               flags = frame.getFlags()
               fuser = frame.getFirstUser()
               luser = frame.getLastUser()

               # The payload size tells us how much valid data is present.
               size = frame.getPayload()

               # Read the full payload into a bytearray.
               full_data = bytearray(size)
               frame.read(full_data, 0)

               # It is also common to copy only a region of interest.
               header = bytearray(min(16, size))
               frame.read(header, 0)

               # NumPy extraction is convenient when the next processing step
               # expects array-like data.
               data_np = frame.getNumpy()

           # Once the data has been copied out, it is safe to process it
           # outside the frame lock.
           if err:
               print(f"drop: chan={chan}, err=0x{err:02x}, flags=0x{flags:04x}")
               return

           print(f"rx chan={chan}, bytes={size}, firstUser={fuser}, lastUser={luser}")
           self.handle_payload(full_data, header, data_np)

       def handle_payload(self,
                          full_data: bytearray,
                          header: bytearray,
                          data_np: np.ndarray):
           print(f"first byte = 0x{full_data[0]:02x}, header bytes = {len(header)}")

The Python receive path is compact because the binding provides several ways to
copy data out of a ``Frame``. ``frame.read(buffer, offset=0)`` copies into any
writable Python buffer object. ``frame.getNumpy(offset=0, count=0)`` returns a
copied ``np.uint8`` array and is convenient for analysis code that already uses
NumPy. ``frame.getMemoryview()`` is also available when a memoryview is the
most natural Python-side representation. In most Python receivers, the common
pattern is to copy the data you need while holding the lock, then release the
lock and do the more expensive application work afterward.

For many applications, this Python pattern is enough. It is easy to instrument,
easy to integrate with Python logging or test code, and a good fit for
bring-up, inspection, and moderate-rate data handling.

C++ Slave Subclass
==================

The C++ receive path follows the same logical flow, but the payload is read more
explicitly. You normally lock the ``Frame``, inspect metadata, then extract the
payload through a ``FrameIterator`` or a more specialized access method. That
is the normal Rogue style because a ``Frame`` is a logical byte stream, not
necessarily a single contiguous block of memory.

This is usually the right choice when the receiver is performance-sensitive,
when it must do substantial processing in C++, or when it needs tight control
over how bytes are copied or interpreted.

.. code-block:: cpp

   #include <algorithm>
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
         ris::FrameIterator it;
         uint32_t x;

         // Hold the ``Frame`` lock while reading payload and metadata.
         auto lock = frame->lock();

         const uint32_t size  = frame->getPayload();
         const uint8_t chan   = frame->getChannel();
         const uint8_t err    = frame->getError();
         const uint16_t flags = frame->getFlags();

         // Get an iterator to the first byte in the ``Frame``.
         it = frame->begin();

         // Direct iterator reads are convenient for a few fixed fields.
         for (x = 0; x < 10 && x < size; x++) {
            printf("Location %u = 0x%02x\n", x, *it);
            ++it;
         }

         // std::copy is the safest general-purpose way to copy the payload
         // out of a ``Frame`` because the iterator handles segmented buffers.
         std::vector<uint8_t> data(size);
         std::copy(frame->begin(), frame->end(), data.begin());

         if (err == 0) {
            process(data.data(), size, chan, flags);
         }
      }

      void process(const uint8_t* data,
                   uint32_t size,
                   uint8_t chan,
                   uint16_t flags) {
         // Application-specific processing
      }
   };

Receive Frame Layout
====================

In practice, many receivers need more than "copy bytes and process". They need
to inspect a header, split the payload into logical regions, and combine that
information with ``Frame`` metadata such as channel, flags, and user fields. The
examples below show that more realistic pattern in both languages.

Python Header And Payload Example
---------------------------------

.. code-block:: python

   # Inside _acceptFrame(self, frame)
   with frame.lock():
       chan = frame.getChannel()
       err = frame.getError()
       flags = frame.getFlags()
       fuser = frame.getFirstUser()
       luser = frame.getLastUser()

       # Copy the full payload once as a uint8 NumPy array.
       raw = frame.getNumpy()

   # Interpret the payload layout after the copy has been made.
   #
   # Layout:
   #   - Header: 4 x uint16 words  = 8 bytes
   #   - Payload: N x uint32 words = variable length
   #   - Tail:   1 x uint16 word   = 2 bytes
   #
   # The payload section therefore occupies everything between byte 8 and the
   # last 2 bytes.
   header_bytes = 8
   tail_bytes = 2

   if raw.size < header_bytes + tail_bytes:
       raise ValueError(f"frame too short: {raw.size} bytes")

   # NumPy views let us reinterpret the copied byte array without taking
   # additional copies.
   header_words = raw[:header_bytes].view(np.uint16)

   payload_bytes = raw[header_bytes:-tail_bytes]
   if payload_bytes.size % 4 != 0:
       raise ValueError(f"payload region is not uint32-aligned: {payload_bytes.size} bytes")
   payload_words = payload_bytes.view(np.uint32)

   tail_word = raw[-tail_bytes:].view(np.uint16)[0]

   if err == 0 and chan == 2:
       self.process_payload(header_words, payload_words, tail_word, flags, fuser, luser)

C++ Header And Payload Example
------------------------------

.. code-block:: cpp

   // Inside acceptFrame(ris::FramePtr frame)
   auto lock = frame->lock();

   const uint32_t size  = frame->getPayload();
   const uint8_t chan   = frame->getChannel();
   const uint8_t err    = frame->getError();
   const uint16_t flags = frame->getFlags();
   const uint8_t fuser  = frame->getFirstUser();
   const uint8_t luser  = frame->getLastUser();

   // Read a fixed-size header from the start of the ``Frame``.
   std::array<uint8_t, 32> header{};
   auto itHdr = frame->begin();
   ris::fromFrame(itHdr, static_cast<uint32_t>(header.size()), header.data());

   // Then read the payload region after the header.
   const uint32_t payloadSize =
      (size > header.size()) ? (size - static_cast<uint32_t>(header.size())) : 0;
   std::vector<uint8_t> payload(payloadSize);
   auto itPay = frame->begin() + static_cast<int32_t>(header.size());
   ris::fromFrame(itPay, payloadSize, payload.data());

   if (err == 0 && chan == 2) {
      processPayload(header.data(), payload.data(), payloadSize, flags, fuser, luser);
   }

Debug Base Slave
================

For bring-up, the base ``Slave`` can be attached directly as a monitor and
configured with ``setDebug(maxBytes, name)`` to print frame summaries and byte
dumps. This is often the fastest way to confirm that ``Frame`` objects are arriving, that
channel numbers and flags look sane, and that the payload begins with the bytes
you expect.

If you want quick byte-dump visibility without writing a custom receiver, this
base-class debug mode is usually the right first step.

Logging
=======

Most custom receive code eventually grows some logging, and there are two
common patterns.

Python receivers usually use normal Python ``logging`` inside ``_acceptFrame()``
or in helper methods called after the frame data has been copied out. C++
receivers usually create a Rogue logger with ``rogue::Logging::create(...)``
inside the receiver class. If you want quick logging without custom code,
``setDebug(maxBytes, name)`` on the base ``Slave`` already emits through a
Rogue C++ logger named ``pyrogue.<name>``. For example,
``dbg.setDebug(128, 'stream.rx.tap')`` emits through ``pyrogue.stream.rx.tap``.

Efficient C++ Payload Reads
===========================

Iterator use is worth spelling out in more detail on the receive side for the
same reason it matters on transmit. A ``Frame`` is a logical byte stream, but
the payload may be spread across multiple underlying ``Buffer`` objects. That
is common for segmented transports and allocators. A ``FrameIterator`` hides
that layout and lets read-side code treat the payload as one continuous stream
of bytes.

That is why ``std::copy`` and helper functions such as ``fromFrame()`` are the
safest general-purpose receive tools. They keep working when the ``Frame`` is split
across multiple buffers, and they let the receiver stay agnostic to the storage
layout used by the upstream path. In most receivers, that is the right default.

There are cases where the iterator overhead matters. If profiling shows that
receive-side copies are a bottleneck, you can copy one contiguous segment at a
time by using the iterator's ``remBuffer()`` and ``ptr()`` helpers.

.. code-block:: cpp

   uint32_t count;
   uint8_t* dst = data;

   it = frame->begin();

   while (it != frame->end()) {
      // Bytes left in the current contiguous region.
      count = it.remBuffer();

      // Copy directly from this contiguous region.
      std::memcpy(dst, it.ptr(), count);

      dst += count;
      it += count;
   }

This approach is more verbose than ``std::copy`` because it makes the segment
boundaries explicit, but it reduces per-byte iterator work inside the copy
loop. It is useful when segmented ``Frame`` objects are common and bulk copy cost matters.

For structured fields at known offsets, ``fromFrame()`` is often the clearest
option because it preserves the iterator semantics while handling the byte count
and iterator advance for you.

.. code-block:: cpp

   uint64_t data64;
   uint32_t data32;
   uint8_t  data8;

   it = frame->begin();

   // Read 64 bits and advance 8 bytes.
   ris::fromFrame(it, 8, &data64);

   // Then 32 bits and advance 4 bytes.
   ris::fromFrame(it, 4, &data32);

   // Then the final byte.
   ris::fromFrame(it, 1, &data8);

If you need high-performance element-level access, use
:ref:`interfaces_stream_frame_accessor` after verifying that the target range
lives in a single contiguous buffer. ``ensureSingleBuffer(frame, true)`` can
flatten a ``Frame`` into one buffer when necessary, but that should be a deliberate
choice because flattening may undo a segmentation strategy chosen by the
upstream path.

Taken together, these receive-side access patterns form a progression. Start
with iterator-based code, because it is robust and matches Rogue's ``Frame`` model.
Move to segment-by-segment contiguous copies only when measurements show the
iterator path is too expensive. Use ``FrameAccessor`` only when you truly need
typed array-style access and can guarantee contiguous storage.

What To Explore Next
====================

- Frame semantics and metadata behavior: :doc:`/stream_interface/frame_model`
- Frame construction and transmit patterns: :doc:`/stream_interface/sending`
- Connection topologies: :doc:`/stream_interface/connecting`
- Stream debugging patterns: :doc:`/stream_interface/debugStreams`

Related Topics
==============

- Building custom C++ extensions: :doc:`/custom_module/index`
- Rogue logging overview: :doc:`/logging/index`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/slave`
  - :doc:`/api/python/rogue/interfaces/stream/frame`

- C++:

  - :doc:`/api/cpp/interfaces/stream/slave`
  - :doc:`/api/cpp/interfaces/stream/frame`
  - :doc:`/api/cpp/interfaces/stream/helpers`
  - :doc:`/api/cpp/interfaces/stream/frameAccessor`
