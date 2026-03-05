.. _interfaces_stream_connecting:
.. _stream_interface_connecting:

==================
Connecting Streams
==================

A stream topology connects sources, processors, and sinks through stream
master/slave links. In practical systems, a hardware ingress source (for
example ``AxiStreamDma``) is often shaped by stream modules and then routed to
an output sink such as a file writer.

Operator syntax and helper functions
====================================

Rogue supports connection operators directly on stream objects:

- ``>>`` for one-way source-to-destination links
- ``<<`` for one-way destination-from-source links
- ``==`` for bi-directional links between dual-role endpoints

Python usage
------------

In Python, operator syntax is generally preferred because it is concise and
reads like a pipeline.

.. code-block:: python

   src >> stage1 >> stage2 >> dst
   dst << src
   ep_a == ep_b

Equivalent helper functions are also available:

.. code-block:: python

   import pyrogue as pr

   pr.streamConnect(src, dst)
   pr.streamConnectBiDir(ep_a, ep_b)

C++ usage
---------

In C++, operator syntax works the same way, but chained expressions require
pointer dereferencing and can become harder to read.

.. code-block:: cpp

   *(*(*src >> fifo) >> rate) >> writer->getChannel(0);
   *epA == epB;

For readability, many users prefer helper macros from
``#include "rogue/Helpers.h"``:

.. code-block:: cpp

   rogueStreamConnect(src, fifo);
   rogueStreamConnect(fifo, rate);
   rogueStreamConnect(rate, writer->getChannel(0));
   rogueStreamConnectBiDir(epA, epB);

Connection semantics and ordering
=================================

- ``master >> slave`` and ``slave << master`` create one-way links.
- ``endpointA == endpointB`` creates links both ways.
- The first slave attached to a master is the primary slave.
- ``reqFrame(size, zeroCopyEn)`` allocation requests go to the primary slave.
- ``sendFrame(frame)`` delivers to secondary slaves first, then the primary.

That final ordering matters if the primary path consumes or empties a
zero-copy frame.

Concrete examples
=================



Fan-out topology: primary processing + diagnostic debug
=======================================================

A common pattern is to keep the primary path unmodified while creating a
secondary branch for reduced-rate diagnostics.

Python
------

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris
   import rogue.utilities.fileio as ruf

   # Open a DMA stream
   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)

   # Primary processing path: fifo + rate limit + file writer
   fifo = ris.Fifo(200, 64, False)
   rate = ris.RateDrop(True, 0.2)  # about 5 Hz
   writer = ruf.StreamWriter()
   writer.open('diagnostic.dat')

   # Dump raw DMA traffic to terminal
   debug = ris.Slave()
   debug.setDebug(64, 'DMA Debug')

   # Connect the streams
   # Attach processing chain first (primary), then add debug branch
   dma >> fifo >> rate >> writer.getChannel(1)
   dma >> debug

C++
---

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/hardware/axi/AxiStreamDma.h"
   #include "rogue/interfaces/stream/Fifo.h"
   #include "rogue/interfaces/stream/RateDrop.h"
   #include "rogue/utilities/fileio/StreamWriter.h"

   namespace rha = rogue::hardware::axi;
   namespace ris = rogue::interfaces::stream;
   namespace ruf = rogue::utilities::fileio;

   int main() {
      auto dma  = rha::AxiStreamDma::create("/dev/datadev_0", 1, true);
      auto fifo = ris::Fifo::create(200, 64, false);
      auto rate = ris::RateDrop::create(true, 0.2);
      auto debug   = ris::Slave::create();
      debug->setDebug(64, "DMA Debug");

      auto writer = ruf::StreamWriter::create();
      writer->open("diagnostic.dat");

      // Attach processing chain first (primary), then add debug branch
      rogueStreamConnect(dma, fifo);
      rogueStreamConnect(fifo, rate);
      rogueStreamConnect(rate, writer->getChannel(1));
      rogueStreamConnect(dma, debug);

      // Equivalent operator-style form:
      // *(*(*dma >> fifo) >> rate) >> writer->getChannel(1);
      // *dma >> debug;

      return 0;
   }

Bi-directional links (DMA <-> TCP bridge)
==========================================

When both endpoints implement stream master and stream slave behavior, ``==``
creates symmetric links in both directions.

Python
------

.. code-block:: python

   import pyrogue as pr
   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)
   net = ris.TcpClient('192.168.1.10', 8000)

   # Preferred operator form
   dma == net


C++
---

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/hardware/axi/AxiStreamDma.h"
   #include "rogue/interfaces/stream/TcpClient.h"

   namespace rha = rogue::hardware::axi;
   namespace ris = rogue::interfaces::stream;

   int main() {
      auto dma = rha::AxiStreamDma::create("/dev/datadev_0", 1, true);
      auto net = ris::TcpClient::create("192.168.1.10", 8000);

      *dma == net;
      // or: rogueStreamConnectBiDir(dma, net);
      return 0;
   }

What to explore next
====================

- Frame production patterns: :doc:`/stream_interface/sending`
- Frame consumption patterns: :doc:`/stream_interface/receiving`
- Built-in module behavior and tuning: :doc:`/stream_interface/built_in_modules`
- Stream section overview: :doc:`/stream_interface/index`
