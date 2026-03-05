.. _interfaces_stream_using_fifo:
.. _stream_interface_using_fifo:

============
Using A Fifo
============

:ref:`interfaces_stream_fifo` inserts a queue between upstream and downstream
stream stages.

Constructor
===========

- Python: ``ris.Fifo(maxDepth, trimSize, noCopy)``
- C++: ``ris::Fifo::create(maxDepth, trimSize, noCopy)``

Parameter behavior
==================

- ``maxDepth``:
  queue depth threshold in frames.
  ``maxDepth > 0`` enables threshold-based drop of incoming frames when full.
  ``maxDepth = 0`` disables that threshold.
- ``trimSize``:
  payload trim limit in bytes for copy mode.
  ``trimSize = 0`` copies full payload.
- ``noCopy``:
  ``True`` enqueues original frame object (trim ignored).
  ``False`` allocates/copies a new frame; metadata is preserved.

Operational counters
====================

Use ``dropCnt()`` to inspect dropped-frame count and ``clearCnt()`` to reset it.

Python example: DMA -> FIFO -> file writer
==========================================

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris
   import rogue.utilities.fileio as ruf

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)
   fifo = ris.Fifo(maxDepth=256, trimSize=0, noCopy=True)

   writer = ruf.StreamWriter()
   writer.open('fifo_capture.dat')

   dma >> fifo >> writer.getChannel(0)

Python tap-path example (copy + trim)
=====================================

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)

   # Main consumer path
   proc = ris.Slave()
   proc.setDebug(32, 'proc')
   dma >> proc

   # Secondary monitoring path: copied and trimmed frames
   tap = ris.Fifo(maxDepth=128, trimSize=64, noCopy=False)
   mon = ris.Slave()
   mon.setDebug(64, 'tap')

   dma >> tap >> mon

C++ example
===========

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/hardware/axi/AxiStreamDma.h"
   #include "rogue/interfaces/stream/Fifo.h"
   #include "rogue/utilities/fileio/StreamWriter.h"

   namespace rha = rogue::hardware::axi;
   namespace ris = rogue::interfaces::stream;
   namespace ruf = rogue::utilities::fileio;

   int main() {
      auto dma  = rha::AxiStreamDma::create("/dev/datadev_0", 1, true);
      auto fifo = ris::Fifo::create(256, 0, true);

      auto writer = ruf::StreamWriter::create();
      writer->open("fifo_capture.dat");

      rogueStreamConnect(dma, fifo);
      rogueStreamConnect(fifo, writer->getChannel(0));
      return 0;
   }

API reference
=============

- :doc:`/api/cpp/interfaces/stream/fifo`

What to explore next
====================

- Filtering and channel selection: :doc:`/stream_interface/filter`
- Rate shaping: :doc:`/stream_interface/rate_drop`
- Topology patterns: :doc:`/stream_interface/connecting`
