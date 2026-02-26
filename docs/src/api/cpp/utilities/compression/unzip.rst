.. _utilities_compression_streamunzip:

.. note::
   Canonical generated C++ API docs are centralized at :ref:`api_reference`.

===========
StreamUnZip
===========

The StreamUnZip class provides a payload decompression engine for Rogue Frames. This module will receive compressed
Frames from an external master, de-compress the Frame payload and then pass the compressed frame to a downstream Slave.

This de-compression module uses the Bzip2 library.


