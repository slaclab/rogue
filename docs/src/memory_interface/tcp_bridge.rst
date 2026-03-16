.. _interfaces_memory_using_tcp:
.. _memory_interface_tcp_bridge:

=================
Memory TCP Bridge
=================

The memory TCP bridge lets a Rogue memory bus cross a TCP connection. It is
provided by the ``TcpServer`` and ``TcpClient`` classes.

You typically use the memory TCP bridge when the software issuing register
transactions cannot run in the same process, or even on the same machine, as
the hardware-facing memory ``Slave``. Common cases include exporting a local SRP
endpoint to a remote control application, splitting a control stack across
processes on one machine, or providing network access to a register bus for a
test or integration tool.

The bridge is asymmetric in a useful way:

- ``TcpClient`` accepts local memory transactions and forwards them over TCP
- ``TcpServer`` receives those transactions and forwards them to its attached
  local memory ``Slave`` or protocol endpoint

Bridge Behavior
===============

- The client side is the local transaction source
- The server side is the local transaction sink
- The bridge uses two consecutive TCP ports

Constructor Parameters
======================

- ``addr``:
  for ``TcpServer``, this is the local bind address or interface;
  for ``TcpClient``, this is the remote server address
- ``port``:
  base port for the bridge; the implementation uses ``port`` and ``port + 1``

Python Server Example
=====================

The server side usually lives in the process that owns the local protocol or
hardware-facing memory endpoint.

.. code-block:: python

   import rogue.interfaces.memory as rim
   import rogue.protocols.srp as rps

   # Local memory SRP bridge
   srpv3 = rps.SrpV3()

   # Listen on all interfaces using ports 8000 and 8001
   tcp = rim.TcpServer('*', 8000)

   # Connect the TCP bridge to the local memory Slave
   tcp >> srpv3

Python Client Example
=====================

The client side usually lives in the process that wants to initiate memory
transactions remotely.

.. code-block:: python

   import rogue.interfaces.memory as rim

   # Local memory Master
   mst = MyMemMaster()

   # Connect to the remote server using ports 8000 and 8001
   tcp = rim.TcpClient('192.168.1.1', 8000)

   # Connect the local Master to the remote bridge
   mst >> tcp

C++ Server Example
==================

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/memory/TcpServer.h"
   #include "rogue/protocols/srp/SrpV3.h"

   namespace rim = rogue::interfaces::memory;
   namespace rps = rogue::protocols::srp;

   int main() {
      // Local memory SRP bridge
      auto srpv3 = rps::SrpV3::create();

      // Listen on all interfaces using ports 8000 and 8001
      auto tcp = rim::TcpServer::create("*", 8000);

      // Connect the TCP bridge to the local memory Slave
      *tcp >> srpv3;
      return 0;
   }

C++ Client Example
==================

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/memory/TcpClient.h"

   namespace rim = rogue::interfaces::memory;

   int main() {
      // Local memory Master
      auto mst = MyMemMaster::create();

      // Connect to the remote server using ports 8000 and 8001
      auto tcp = rim::TcpClient::create("192.168.1.1", 8000);

      // Connect the local Master to the remote bridge
      *mst >> tcp;
      return 0;
   }

Loopback Process Split
======================

The memory TCP bridge is also useful when two programs on the same machine need
to share one register bus without sharing in-process Rogue objects. In that
case, use loopback addressing such as ``127.0.0.1`` and publish a
``TcpServer`` from one process while the second process connects with
``TcpClient``.

This pattern is often useful when one process owns the hardware-facing stack
and a second process provides control, automation, or user-interface logic.

Logging
=======

The memory TCP bridge uses Rogue C++ logging.

Logger name patterns are:

- ``pyrogue.memory.TcpServer.<addr>.<port>``
- ``pyrogue.memory.TcpClient.<addr>.<port>``

Examples:

- ``pyrogue.memory.TcpServer.*.8000``
- ``pyrogue.memory.TcpClient.127.0.0.1.8000``
- Unified Logging API:
  ``logging.getLogger('pyrogue.memory.TcpServer').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.memory.TcpServer', rogue.Logging.Debug)``

Enable the logger before constructing the bridge object:

.. code-block:: python

   import rogue
   import rogue.interfaces.memory as rim

   rogue.Logging.setFilter('pyrogue.memory.TcpServer', rogue.Logging.Debug)
   server = rim.TcpServer('*', 8000)

At debug level these classes log socket setup and transaction forwarding
details. There is no additional per-instance runtime debug helper.

What To Explore Next
====================

- Bus connection patterns: :doc:`/memory_interface/connecting`
- Custom ``Master`` patterns: :doc:`/memory_interface/master`
- Custom ``Slave`` patterns: :doc:`/memory_interface/slave`
- Transaction lifecycle details: :doc:`/memory_interface/transactions`

Related Topics
==============

- Stream TCP bridge: :doc:`/stream_interface/tcp_bridge`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/memory/tcpserver`
  - :doc:`/api/python/rogue/interfaces/memory/tcpclient`

- C++:

  - :doc:`/api/cpp/interfaces/memory/tcpServer`
  - :doc:`/api/cpp/interfaces/memory/tcpClient`
