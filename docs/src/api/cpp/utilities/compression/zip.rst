.. _utilities_compression_streamzip:

.. note::
   Canonical generated C++ API docs are centralized at :ref:`api_reference`.

=========
StreamZip
=========

The StreamZip class provides a payload compression engine for Rogue Frames. This module will receive Frames from
an external master, compress the Frame payload and then pass the compressed frame to a downstream Slave.

This compression module uses the Bzip2 library.


