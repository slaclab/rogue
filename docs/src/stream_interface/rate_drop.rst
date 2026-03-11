.. _interfaces_stream_using_rate_drop:
.. _stream_interface_using_rate_drop:

========================
Using A Rate Drop Object
========================

:ref:`interfaces_stream_rate_drop` limits forwarded frame rate before
slow downstream consumers.

Constructor
===========

- Python: ``ris.RateDrop(period, value)``
- C++: ``ris::RateDrop::create(period, value)``

Parameter behavior
==================

- ``period=True`` (time mode):
  ``value`` is seconds between forwarded frames.
  Example: ``value=0.1`` forwards at about 10 Hz.
- ``period=False`` (count mode):
  ``value`` is drop-count target. One frame is forwarded, then roughly
  ``value`` frames are suppressed before forwarding again.
  Example: ``value=10`` keeps about 1 out of every 11 frames.
- ``value=0`` in count mode effectively disables dropping.

Python period-mode example
==========================

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris
   import rogue.utilities.fileio as ruf

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)
   rate = ris.RateDrop(period=True, value=0.1)

   writer = ruf.StreamWriter()
   writer.open('rate_10hz.dat')

   dma >> rate >> writer.getChannel(0)

Python count-mode example
=========================

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)

   # Keep one frame, drop about ten
   keep_sparse = ris.RateDrop(period=False, value=10)

   dbg = ris.Slave()
   dbg.setDebug(64, 'sparse')

   dma >> keep_sparse >> dbg

C++ example
===========

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/hardware/axi/AxiStreamDma.h"
   #include "rogue/interfaces/stream/RateDrop.h"
   #include "rogue/utilities/fileio/StreamWriter.h"

   namespace rha = rogue::hardware::axi;
   namespace ris = rogue::interfaces::stream;
   namespace ruf = rogue::utilities::fileio;

   int main() {
      auto dma  = rha::AxiStreamDma::create("/dev/datadev_0", 1, true);
      auto rate = ris::RateDrop::create(true, 0.1);

      auto writer = ruf::StreamWriter::create();
      writer->open("rate_10hz.dat");

      rogueStreamConnect(dma, rate);
      rogueStreamConnect(rate, writer->getChannel(0));
      return 0;
   }

What to explore next
====================

- FIFO buffering and burst absorption: :doc:`/stream_interface/fifo`
- Channel/error selection: :doc:`/stream_interface/filter`
- Topology design: :doc:`/stream_interface/connecting`

API Reference
=============

- Python: :doc:`/api/python/interfaces_stream_ratedrop`
- C++: :doc:`/api/cpp/interfaces/stream/rateDrop`
