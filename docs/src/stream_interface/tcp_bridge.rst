.. _interfaces_stream_using_tcp:
.. _stream_interface_using_tcp:

====================
Using The TCP Bridge
====================

Rogue stream TCP bridging is provided by ``TcpServer`` and ``TcpClient``
(wrappers around ``TcpCore``).

Bridge behavior
===============

- Full-duplex stream transport.
- Uses two consecutive TCP ports.
- Preserves frame metadata (flags, channel, error) and payload bytes.
- Send path is blocking when remote side is absent or back-pressuring.

Same-machine inter-process use (loopback)
=========================================

TCP bridge endpoints are also useful for connecting separate processes on the
same host. Use loopback addressing (``127.0.0.1``) so one process can publish
or consume stream traffic from another without shared in-process objects.

Typical split:

- Process A: owns hardware-facing endpoint(s), exports via ``TcpServer``.
- Process B: connects with ``TcpClient`` and performs analysis/logging/GUI work.

Constructor parameters
======================

- ``addr``:
  server mode: local bind address/interface.
  client mode: remote server address.
- ``port``:
  base port. Bridge uses ``port`` and ``port+1``.

Address/port mapping
====================

Given base port ``P``:

- Server binds on ``P`` and ``P+1``.
- Client connects to server on ``P`` and ``P+1``.

Python server example
=====================

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)
   rx_local = ris.Slave()
   rx_local.setDebug(64, 'tcp.server.rx')

   tcp = ris.TcpServer('127.0.0.1', 8000)

   # Local tx path over network, then back into a local receiver
   dma >> tcp >> rx_local

Python client example (DMA endpoint)
====================================

.. code-block:: python

   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)
   tcp = ris.TcpClient('192.168.1.10', 8000)

   # Bi-directional DMA <-> network bridge
   dma == tcp

C++ server/client example
=========================

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/hardware/axi/AxiStreamDma.h"
   #include "rogue/interfaces/stream/TcpClient.h"
   #include "rogue/interfaces/stream/TcpServer.h"

   namespace rha = rogue::hardware::axi;
   namespace ris = rogue::interfaces::stream;

   int main() {
      auto server = ris::TcpServer::create("127.0.0.1", 8000);
      auto client = ris::TcpClient::create("127.0.0.1", 8000);

      // Loopback-style bridge wiring between two endpoints
      rogueStreamConnectBiDir(server, client);

      auto dma = rha::AxiStreamDma::create("/dev/datadev_0", 1, true);
      rogueStreamConnectBiDir(dma, client);
      return 0;
   }

API reference
=============

- :doc:`/api/cpp/interfaces/stream/tcpCore`
- :doc:`/api/cpp/interfaces/stream/tcpServer`
- :doc:`/api/cpp/interfaces/stream/tcpClient`

Operational notes
=================

- For many parallel bridges, tune OS file-descriptor/process limits.
- Call ``stop()``/``close()`` during controlled shutdown paths.

What to explore next
====================

- Bidirectional connection semantics: :doc:`/stream_interface/connecting`
- Receive-side error/channel handling: :doc:`/stream_interface/receiving`
- Rate control or buffering before bridge: :doc:`/stream_interface/rate_drop`,
  :doc:`/stream_interface/fifo`
