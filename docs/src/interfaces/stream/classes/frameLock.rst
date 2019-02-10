.. _interfaces_stream_frame_lock:

Frame Lock
==========

The FrameLock class is a container for a lock on a :ref:`interfaces_stream_frame` object. This lock
is created and returned by calling the lock() method on a Frame. The lock is released when the
FrameLock oject is deleted.

FrameLock objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::FrameLockPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::FrameLock
   :members:

