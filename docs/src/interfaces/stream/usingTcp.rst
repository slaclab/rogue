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

   # Start a TCP Bridge Server, Listen on ports 8000 & 8001 on localhost
   # Pass an address of 192.168.1.1 to listen on only that specific interface
   tcp = rogue.interfaces.stream.TcpServer("127.0.0.1",8000)

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

   // Start a TCP Bridge Server, Listen on localhost, ports 8000 & 8001.
   // Pass an address of 192.168.1.1 to listen on only that specific interface
   rogue::interfaces::stream::TcpServerPtr tcp = rogue::interfaces::stream::TcpServer::create("127.0.0.1",8000)

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

Resource Configuration For Multiple Streams
===========================================

To use multiple rogue streams, ensure that the appropriate operating-system-level settings have been enabled.  The following (non-optimized) settings allow for the parallel launch of 2043 TCP servers on a RedHat Enterprise Linux 7.9 machine.  See the steps below.

Use sysctl calls to set max number of open files/sockets, threads and max_map_count::

    sysctl -w fs.file-max=262140
    sysctl -w kernel.threads-max=1014712
    sysctl -w vm.max_map_count=2097152

Confirm with::

    cat /proc/sys/fs/file-max
    cat /proc/sys/kernel/threads-max
    cat /proc/sys/vm/max_map_count

Edit /etc/security/limits.conf and add the following::

    * soft     nproc          8192
    * hard     nproc          8192
    * soft     nofile         524280
    * hard     nofile         524280

Ensure the following limits::

    (rogue_build) [skoufis@pc94331 ~]$ ulimit -a
    core file size          (blocks, -c) 0
    data seg size           (kbytes, -d) unlimited
    scheduling priority             (-e) 0
    file size               (blocks, -f) unlimited
    pending signals                 (-i) 126839
    max locked memory       (kbytes, -l) 64
    max memory size         (kbytes, -m) unlimited
    open files                      (-n) 524280
    pipe size            (512 bytes, -p) 8
    POSIX message queues     (bytes, -q) 819200
    real-time priority              (-r) 0
    stack size              (kbytes, -s) 8192
    cpu time               (seconds, -t) unlimited
    max user processes              (-u) 8192
    virtual memory          (kbytes, -v) unlimited
    file locks                      (-x) unlimited
