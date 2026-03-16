.. _stream_interface_frame_model:

===========
Frame Model
===========

``Frame`` is the data and metadata container passed through Rogue stream
connections.

What a frame carries
====================

- Payload bytes.
- Channel tag (``getChannel``/``setChannel``).
- Error code (``getError``/``setError``).
- Flags/user fields (``getFlags``/``setFlags``, ``setFirstUser``,
  ``setLastUser``).

Capacity vs payload
===================

- ``getSize()``: total writable frame capacity in bytes.
- ``getPayload()``: bytes currently marked valid.
- ``getAvailable()``: remaining writable bytes.

Write APIs grow payload as needed, up to frame capacity. Writes beyond
``getSize()`` raise an exception.

Locking model
=============

Use ``with frame.lock():`` in Python or ``auto lock = frame->lock();`` in C++
when mutating or reading payload and metadata in shared execution paths.

Python access patterns
======================

- ``frame.write(obj, offset=0)``: write from Python buffer object.
- ``frame.read(obj, offset=0)``: read into Python buffer object.
- ``frame.putNumpy(arr, offset=0)``: NumPy-specific write path.
- ``frame.getNumpy(offset=0, count=0)``: copy payload bytes into ``np.uint8``
  array.
- ``frame.getMemoryview()``: get memoryview over copied frame bytes.

``write`` accepts buffer-compatible objects (bytes/bytearray/contiguous NumPy
arrays). ``putNumpy`` is safer for non-contiguous NumPy arrays.

C++ access patterns
===================

- ``FrameIterator`` with ``toFrame``/``fromFrame`` for buffer-safe access over
  multi-buffer payloads.
- ``FrameAccessor<T>`` for contiguous typed access when range fits one buffer.
- ``ensureSingleBuffer(frame, true)`` (from ``Master``/``Slave``) to flatten
  when contiguous access is required.

Related references
==================

- C++ API reference: :doc:`/api/cpp/interfaces/stream/frame`
- Iterators and helpers: :doc:`/api/cpp/interfaces/stream/frameIterator`,
  :doc:`/api/cpp/interfaces/stream/helpers`
- Accessor: :doc:`/api/cpp/interfaces/stream/frameAccessor`
- Send/receive usage: :doc:`/stream_interface/sending`,
  :doc:`/stream_interface/receiving`
