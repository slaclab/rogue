.. _interfaces_memory_using_tcp:
.. _memory_interface_tcp_bridge:

====================
Using The TCP Bridge
====================

Memory TCP bridge endpoints (``TcpServer`` and ``TcpClient``) forward Rogue
memory transactions across process or host boundaries.

Bridge behavior
===============

- Client accepts local memory transactions and forwards to server.
- Server forwards to its attached local memory slave/protocol endpoint.
- Uses two consecutive TCP ports.

Same-machine inter-process use (loopback)
=========================================

Memory TCP bridge is useful for splitting control stacks across processes on
one host. Use ``127.0.0.1`` to expose a server in one process and attach a
client in another.

Constructor parameters
======================

- ``addr``:
  server mode: local bind address/interface.
  client mode: remote server address.
- ``port``:
  base port. Bridge uses ``port`` and ``port+1``.

Python server example
=====================

.. code-block:: python

   import rogue.interfaces.memory as rim
   import rogue.protocols.srp as rps

   srpv3 = rps.SrpV3()
   tcp = rim.TcpServer('*', 8000)

   tcp >> srpv3

Python client example
=====================

.. code-block:: python

   import rogue.interfaces.memory as rim

   mst = MyMemMaster()
   tcp = rim.TcpClient('192.168.1.10', 8000)

   mst >> tcp

C++ example
===========

.. code-block:: cpp

   #include "rogue/interfaces/memory/TcpClient.h"
   #include "rogue/interfaces/memory/TcpServer.h"
   #include "rogue/protocols/srp/SrpV3.h"

   namespace rim = rogue::interfaces::memory;
   namespace rps = rogue::protocols::srp;

   int main() {
      auto srpv3 = rps::SrpV3::create();
      auto server = rim::TcpServer::create("*", 8000);
      auto client = rim::TcpClient::create("127.0.0.1", 8000);

      *server >> srpv3;
      // Example local master would connect to client in its process
      // *master >> client;
      return 0;
   }

API reference
=============

- Python: :doc:`/api/python/rogue/interfaces/memory_tcpserver`
- Python: :doc:`/api/python/rogue/interfaces/memory_tcpclient`
- C++: :doc:`/api/cpp/interfaces/memory/tcpServer`
- C++: :doc:`/api/cpp/interfaces/memory/tcpClient`

Logging
=======

The memory TCP bridge uses Rogue C++ logging.

Logger name patterns are:

- ``pyrogue.memory.TcpServer.<addr>.<port>``
- ``pyrogue.memory.TcpClient.<addr>.<port>``

Examples:

- ``pyrogue.memory.TcpServer.*.8000``
- ``pyrogue.memory.TcpClient.127.0.0.1.8000``

Enable logging with ``rogue.Logging.setFilter(...)`` before constructing the
bridge object:

.. code-block:: python

   import rogue
   import rogue.interfaces.memory as rim

   rogue.Logging.setFilter('pyrogue.memory.TcpServer', rogue.Logging.Debug)
   server = rim.TcpServer('*', 8000)

At debug level these classes log socket setup and transaction forwarding
details. There is no additional per-instance runtime debug helper.

What to explore next
====================

- Bus connection patterns: :doc:`/memory_interface/connecting`
- Custom master/slave examples: :doc:`/memory_interface/master`,
  :doc:`/memory_interface/slave`
