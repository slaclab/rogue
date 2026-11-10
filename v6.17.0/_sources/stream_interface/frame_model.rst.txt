.. _stream_interface_frame_model:

===========
Frame Model
===========

``Frame`` is the data and metadata container that moves through Rogue stream
connections. Every send, receive, buffer, filter, or bridge operation in the
stream interface is ultimately acting on a ``Frame``.

A ``Frame`` carries two kinds of information. The first is payload bytes. The
second is metadata that tells the rest of the stream graph how that payload
should be interpreted or routed. Understanding that split is the key to reading
the rest of the stream documentation.

What A ``Frame`` Carries
========================

A ``Frame`` contains:

- Payload bytes
- Channel metadata via ``getChannel()`` and ``setChannel()``
- Error metadata via ``getError()`` and ``setError()``
- Flags and user fields via ``getFlags()``, ``setFlags()``, ``setFirstUser()``,
  and ``setLastUser()``

The payload is the byte stream itself. The metadata travels with the payload
and lets downstream code decide how to decode, route, filter, or reject the
``Frame`` without reparsing the payload when a simple metadata check is enough.

Capacity And Payload
====================

Three size-related methods appear often in stream code:

- ``getSize()`` returns the total writable capacity of the ``Frame`` in bytes
- ``getPayload()`` returns how many bytes are currently marked valid
- ``getAvailable()`` returns how much writable capacity remains

This distinction matters because a ``Frame`` may have enough allocated storage
for more bytes than are currently valid. Write operations grow the valid payload
as needed, up to the ``Frame`` capacity. Writes beyond ``getSize()`` raise an
exception.

Locking Model
=============

Because a ``Frame`` may be shared across multiple stages, payload and metadata
access should be protected by the ``Frame`` lock when code is reading or
modifying shared state:

- Python: ``with frame.lock():``
- C++: ``auto lock = frame->lock();``

It is common to copy the data you need while holding the lock, then release the
lock before doing more expensive application work.

Python Access Patterns
======================

Python bindings provide several convenient ways to access ``Frame`` contents:

- ``frame.write(obj, offset=0)`` writes from a Python buffer object
- ``frame.read(obj, offset=0)`` reads into a writable Python buffer object
- ``frame.putNumpy(arr, offset=0)`` writes from a NumPy array
- ``frame.getNumpy(offset=0, count=0)`` returns a copied ``np.uint8`` array
- ``frame.getMemoryview()`` returns a memoryview over copied ``Frame`` bytes

``write()`` accepts ordinary Python buffer-compatible objects such as
``bytes``, ``bytearray``, and contiguous NumPy arrays. ``putNumpy()`` is the
more explicit and usually safer choice when the source is a NumPy array,
especially if the array may be non-contiguous.

C++ Access Patterns
===================

The C++ side exposes more of the ``Frame`` layout and is designed to support
both correctness-first and performance-oriented access styles.

- ``FrameIterator`` with ``toFrame()`` and ``fromFrame()`` is the safest
  general-purpose access method across multi-buffer payloads
- ``FrameAccessor<T>`` provides typed contiguous access when the requested range
  fits within one underlying buffer
- ``ensureSingleBuffer(frame, true)`` can flatten a ``Frame`` when contiguous
  access is required

The important detail is that a ``Frame`` payload does not have to live in one
contiguous memory block. It may span multiple underlying ``Buffer`` objects.
That is why iterator-based access appears so often in Rogue examples.

What To Explore Next
====================

- Connection semantics: :doc:`/stream_interface/connecting`
- Transmit-side ``Frame`` construction: :doc:`/stream_interface/sending`
- Receive-side ``Frame`` inspection: :doc:`/stream_interface/receiving`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/frame`

- C++:

  - :doc:`/api/cpp/interfaces/stream/frame`
  - :doc:`/api/cpp/interfaces/stream/frameIterator`
  - :doc:`/api/cpp/interfaces/stream/helpers`
  - :doc:`/api/cpp/interfaces/stream/frameAccessor`
