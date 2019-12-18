.. _interfaces_stream_using_tcp:

====================
Using The TCP Bridge
====================

The stream TCP bridge classes allows a Rogue stream to be bridged over a TCP network interface. The bridge
consists of a server and a client. The server, :ref:`interfaces_stream_tcp_server`, listens for incoming 
connections on a pair of TCP ports.  The client, :ref:`interfaces_stream_tcp_client`, connects to the server 
at a specific address. Both ends of the bridge are bi-directional allowing a full duplex stream to be bridged
between the server and client.

Python Server
=============

The following code demonstrates a Python server with a local receiver and transmitter device.  The local transmitter 
will send data to a remote receiver on the client. The local receiver will receive data from a remote transmitter 
on the client. The Python server is able to interface with either a Python or C++ client.

.. code-block:: python

   import rogue.interfaces.stream
   import pyrogue

   # Local transmitter
   src = MyCustomMaster()

   # Local receiver
   dst = MyCustomSlave()

   # Start a TCP Bridge Server, Listen on ports 8000 & 8001 on all interfaces
   # Pass an address of 192.168.1.1 to listen on only that specific interface
   tcp = rogue.interfaces.stream.TcpServer("*",8000)

   # Connect the transmitter and the receiver
   src >> tcp >> dst

Python Client
=============

The following code demonstrates a Python client with a local receiver and transmitter device. The local transmitter 
will send data to a remote receiver on the server. The local receiver will receive data from a remote transmitter 
on the server.  The Python client is able to interface with either a Python or C++ server. 

.. code-block:: python

   import rogue.interfaces.stream
   import pyrogue

   # Local transmitter
   src = MyCustomMaster()

   # Local receiver
   dst = MyCustomSlave()

   # Start a TCP Bridge Client, Connect remote server at 192.168.1.1 ports 8000 & 8001.
   tcp = rogue.interfaces.stream.TcpClient("192.168.1.1",8000)

   # Connect the transmitter and the receiver
   src >> tcp >> dst


C++ Server
==========

The following code demonstrates a C++ server with a local receiver and transmitter device. The local transmitter 
will send data to a remote receiver on the client. The local receiver will receive data from a remote transmitter 
on the client.  The C++ server is able to interface with either a Python or C++ client. 

.. code-block:: c

   #include <rogue/interfaces/stream/TcpServer.h>

   // Local transmitter
   MyCustomMasterPtr src = MyCustomMaster::create()

   // Local receiver
   MyCustomSlavePtr dst = MyCustomSlave::create()

   // Start a TCP Bridge Server, Listen on all interfaces, ports 8000 & 8001.
   // Pass an address of 192.168.1.1 to listen on only that specific interface
   rogue::interfaces::stream::TcpServerPtr tcp = rogue::interfaces::stream::TcpServer::create("*",8000)

   // Connect the transmitter
   *( *src >> tcp ) >> dst;

C++ Client
==========

The following code demonstrates a C++ client with a local receiver and transmitter device.  The local transmitter 
will send data to a remote receiver on the server. The local receiver will receive data from a remote transmitter 
on the server.  The C++ client is able to interface with either a Python or C++ server.

.. code-block:: c

   #include <rogue/interfaces/stream/TcpClient.h>

   // Local transmitter
   MyCustomMasterPtr src = MyCustomMaster::create()

   // Local receiver
   MyCustomSlavePtr dst = MyCustomSlave::create()

   // Start a TCP Bridge Client, Connect remote server at 192.168.1.1 ports 8000 & 8001.
   rogue::interfaces::stream::TcpClientPtr tcp = rogue::interfaces::stream::TcpClient::create("192.168.1.1",8000)

   // Connect the transmitter
   *( *src >> tcp ) >> dst;

