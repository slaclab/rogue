.. _interfaces_stream_debug_streams:
.. _stream_interface_debug_streams:

=================
Debugging Streams
=================

For bring-up, attach a base :ref:`interfaces_stream_slave` as a passive
monitor and enable log output with ``setDebug(maxBytes, name)``.

Parameter behavior
==================

- ``maxBytes``: maximum payload bytes shown per received frame.
- ``name``: logger name prefix used in emitted debug messages.

Logging
=======

``setDebug(maxBytes, name)`` uses Rogue C++ logging, not Python ``logging``.

- Dynamic logger pattern: ``pyrogue.<name>``
- Example: ``dbg.setDebug(100, 'stream.debug')`` logs through
  ``pyrogue.stream.debug``
- Configuration API:
  ``rogue.Logging.setFilter('pyrogue.stream.debug', rogue.Logging.Debug)``

Set the filter before calling ``setDebug(...)``. The helper creates the logger
instance when debug mode is enabled.

Python example
==============

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)

   dbg = ris.Slave()
   dbg.setDebug(100, 'stream.debug')

   # Monitor path
   dma >> dbg

C++ example
===========

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/hardware/axi/AxiStreamDma.h"
   #include "rogue/interfaces/stream/Slave.h"

   namespace rha = rogue::hardware::axi;
   namespace ris = rogue::interfaces::stream;

   int main() {
      auto dma = rha::AxiStreamDma::create("/dev/datadev_0", 1, true);
      auto dbg = ris::Slave::create();

      dbg->setDebug(100, "stream.debug");
      rogueStreamConnect(dma, dbg);
      return 0;
   }

Notes
=====

- Base ``Slave`` debug mode increments internal frame/byte counters.
- The logger name is chosen entirely by the ``name`` argument passed to
  ``setDebug(...)``.
- If a custom C++ slave overrides ``acceptFrame`` and still needs base
  counters/debug behavior, call ``Slave::acceptFrame(frame)`` or implement
  equivalent logic.

API reference
=============

- :doc:`/api/cpp/interfaces/stream/slave`

What to explore next
====================

- Connection placement patterns: :doc:`/stream_interface/connecting`
- Receive-side frame handling: :doc:`/stream_interface/receiving`
- FIFO/RateDrop tap-path controls: :doc:`/stream_interface/fifo`,
  :doc:`/stream_interface/rate_drop`
