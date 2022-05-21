.. _interfaces_memory_using_tcp:

====================
Using The TCP Bridge
====================

The memory TCP bridge classes allows a Rogue memory interface to be bridged over a TCP network interface. 
The bridge consists of a server and a client. The server, :ref:`interfaces_memory_tcp_server`, listens for 
incoming connections on a pair of TCP ports.  The client, :ref:`interfaces_memory_tcp_client`, connects to 
the server at a specific address. The client will accept memory bus transactions and forward them to the server.

Python Server
=============

The following code demonstrates a Python server with a local memory slave.  The Python server is 
able to interface with either a Python or C++ client.

.. code-block:: python

   import rogue.interfaces.memory
   import rogue.protocols.srp
   import pyrogue

   # Local memory SrpV3 bridge
   srpv3 = rogue.protocols.srp.SrpV3()

   # Start a TCP Bridge Server, Listen on ports 8000 & 8001 on all interfaces
   # Pass an address of 192.168.1.1 to listen on only that specific interface
   tcp = rogue.interfaces.memory.TcpServer("*",8000)

   # Connect the bus
   tcp >> srpV3

Python Client
=============

The following code demonstrates a Python client with a local memory bus master. The Python client is able 
to interface with either a Python or C++ server. 

.. code-block:: python

   import rogue.interfaces.memory
   import pyrogue

   # Memory bus master (from master example)
   mst = MyMaster()

   # Start a TCP Bridge Client, Connect remote server at 192.168.1.1 ports 8000 & 8001.
   tcp = rogue.interfaces.memory.TcpClient("192.168.1.1",8000)

   # Connect the bus
   mst >> tcp

C++ Server
==========

The following code demonstrates a C++ server with a local memory slave.  The C++ server is 
able to interface with either a Python or C++ client.

.. code-block:: c

   #include <rogue/interfaces/memory/TcpServer.h>
   #include <rogue/protocols/srp/SrpV3.h>

   // Local memory SrpV3 bridge
   rogue::protocols::srp::SrpV3Ptr srpv3 = rogue.protocols.srp.SrpV3::create();

   // Start a TCP Bridge Server, Listen on ports 8000 & 8001 on all interfaces
   // Pass an address of 192.168.1.1 to listen on only that specific interface
   rogue::interfaces::memory::TcpServerPtr tcp = rogue.interfaces.memory.TcpServer::create("*",8000);

   // Connect the bus
   *tcp >> srpV3;

C++ Client
==========

The following code demonstrates a C++ client with a local memory bus master. The C++ client is able 
to interface with either a Python or C++ server. 

.. code-block:: c

   #include <rogue/interfaces/memory/TcpClient.h>

   // Memory bus master (from master example)
   MyMasterPtr mst = MyMaster::create();

   // Start a TCP Bridge Client, Connect remote server at 192.168.1.1 ports 8000 & 8001.
   rogue::interfaces::memory::TcpClientPtr tcp = rogue::interfaces::memory::TcpClient::create("192.168.1.1",8000);

   // Connect the bus
   *mst >> tcp;

