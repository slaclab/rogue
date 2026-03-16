.. _interfaces_stream_using_tcp:
.. _stream_interface_using_tcp:

=================
Stream TCP Bridge
=================

Rogue stream TCP bridging is provided by ``TcpServer`` and ``TcpClient``. These
objects let a stream topology cross a TCP connection while preserving payload
bytes and ``Frame`` metadata.

You typically use the TCP bridge when the producer and consumer cannot live in
the same process. Common cases include exporting a hardware-facing process to a
remote analysis application, splitting acquisition and GUI work across two
programs on the same machine, or moving a stream between computers without
changing the rest of the stream graph.

Both ends of the bridge are bi-directional. A local ``Master`` can send
``Frame`` objects to the remote side, and a local ``Slave`` can receive
``Frame`` objects coming back in the other direction. In practice, that means a
single TCP bridge object can sit between local transmit and receive paths.

Bridge Behavior
===============

- Full-duplex stream transport
- Uses two consecutive TCP ports
- Preserves payload bytes and ``Frame`` metadata
- Send path blocks when the remote side is absent or back-pressuring

Constructor Parameters
======================

- ``addr``:
  for ``TcpServer``, this is the local bind address or interface;
  for ``TcpClient``, this is the remote server address
- ``port``:
  base port for the bridge; the implementation uses ``port`` and ``port + 1``

Address And Port Mapping
========================

Given base port ``P``:

- ``TcpServer`` binds on ``P`` and ``P+1``
- ``TcpClient`` connects to the server on ``P`` and ``P+1``

Python Server Example
=====================

The server side usually lives with the hardware-facing or locally owned stream
endpoints.

.. code-block:: python

   import rogue.interfaces.stream as ris

   # Local transmitter
   src = MyCustomMaster()

   # Local receiver
   dst = MyCustomSlave()

   # Listen on localhost using ports 8000 and 8001
   tcp = ris.TcpServer('127.0.0.1', 8000)

   # The local transmitter sends to the remote client, and the local receiver
   # accepts data arriving from the remote client.
   src >> tcp >> dst

Python Client Example
=====================

The client side usually runs in the remote or secondary process.

.. code-block:: python

   import rogue.interfaces.stream as ris

   # Local transmitter
   src = MyCustomMaster()

   # Local receiver
   dst = MyCustomSlave()

   # Connect to the remote server using ports 8000 and 8001
   tcp = ris.TcpClient('192.168.1.1', 8000)

   # The local transmitter sends to the remote server, and the local receiver
   # accepts data arriving from the remote server.
   src >> tcp >> dst

C++ Server Example
==================

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/stream/TcpServer.h"
   #include "MyCustomMaster.h"
   #include "MyCustomSlave.h"

   int main() {
      // Local transmitter
      auto src = MyCustomMaster::create();

      // Local receiver
      auto dst = MyCustomSlave::create();

      // Listen on localhost using ports 8000 and 8001
      auto tcp = rogue::interfaces::stream::TcpServer::create("127.0.0.1", 8000);

      rogueStreamConnect(src, tcp);
      rogueStreamConnect(tcp, dst);
      return 0;
   }

C++ Client Example
==================

.. code-block:: cpp

   #include "rogue/Helpers.h"
   #include "rogue/interfaces/stream/TcpClient.h"
   #include "MyCustomMaster.h"
   #include "MyCustomSlave.h"

   int main() {
      // Local transmitter
      auto src = MyCustomMaster::create();

      // Local receiver
      auto dst = MyCustomSlave::create();

      // Connect to the remote server using ports 8000 and 8001
      auto tcp = rogue::interfaces::stream::TcpClient::create("192.168.1.1", 8000);

      rogueStreamConnect(src, tcp);
      rogueStreamConnect(tcp, dst);
      return 0;
   }

Loopback Process Split
======================

The TCP bridge is also useful when two programs on the same machine need to
exchange stream traffic without sharing in-process Rogue objects. In that case,
use loopback addressing such as ``127.0.0.1`` and let one process publish a
``TcpServer`` while the other connects with ``TcpClient``.

This pattern is common when one process owns a hardware device and a second
process performs analysis, logging, or UI work.

Logging
=======

``TcpCore`` uses Rogue C++ logging rather than Python ``logging``. The logger
name is constructed dynamically from the address, mode, and port:

- ``pyrogue.stream.TcpCore.<addr>.Server.<port>``
- ``pyrogue.stream.TcpCore.<addr>.Client.<port>``

Examples:

- ``pyrogue.stream.TcpCore.127.0.0.1.Server.8000``
- ``pyrogue.stream.TcpCore.192.168.1.10.Client.8000``
- Unified Logging API:
  ``logging.getLogger('pyrogue.stream.TcpCore').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.stream.TcpCore', rogue.Logging.Debug)``

You can enable a broad filter before or after constructing the bridge. Enable
it before construction only if you want constructor or initial connection
startup messages in addition to later implementation messages:

.. code-block:: python

   import rogue
   import rogue.interfaces.stream as ris

   rogue.Logging.setFilter('pyrogue.stream.TcpCore', rogue.Logging.Debug)
   tcp = ris.TcpClient('127.0.0.1', 8000)

You can also target one specific bridge instance when the full dynamic logger
name is known.

.. code-block:: python

   logging.getLogger(
       'pyrogue.stream.TcpCore.127.0.0.1.Client.8000'
   ).setLevel(logging.DEBUG)

What It Logs
------------

At debug level, ``TcpCore`` logs bridge setup details and frame movement, such
as:

- Client/server socket creation
- Bind/connect address selection
- Pushed frame sizes
- Pulled frame sizes
- Worker-thread identity

There is no additional per-instance ``setDebug(...)`` helper on ``TcpCore``.
For byte-level frame inspection, add a separate debug ``Slave`` or use
``setDebug(...)`` on a plain ``rogue.interfaces.stream.Slave`` tap elsewhere in
the stream graph.

Operational Notes
=================

For a small number of bridges, the default operating-system limits are usually
fine. For many parallel TCP bridge instances, file-descriptor and process limits
may need to be tuned at the operating-system level.

During controlled shutdown paths, call ``stop()`` or ``close()`` where
appropriate so the bridge threads and sockets are released cleanly.

Resource Configuration For Multiple Streams
===========================================

If a system needs to host many parallel TCP bridge instances, the limiting
factor is often not Rogue itself but the operating-system resource limits around
open files, sockets, threads, and memory mappings. The older stream
documentation included a concrete Linux tuning example for this case, and that
guidance is still useful when scaling to large numbers of bridges.

The example below was used on a Red Hat Enterprise Linux 7.9 machine to support
the parallel launch of many TCP servers. The values are not universal tuning
recommendations, but they illustrate the kinds of limits that may need to be
raised.

Use ``sysctl`` to adjust system-wide limits such as open files, threads, and
memory maps:

.. code-block:: bash

   sysctl -w fs.file-max=262140
   sysctl -w kernel.threads-max=1014712
   sysctl -w vm.max_map_count=2097152

Confirm the resulting values:

.. code-block:: bash

   cat /proc/sys/fs/file-max
   cat /proc/sys/kernel/threads-max
   cat /proc/sys/vm/max_map_count

User-level process and file limits may also need to be increased. One way to do
that is by adding entries like the following to ``/etc/security/limits.conf``:

.. code-block:: text

   * soft     nproc          8192
   * hard     nproc          8192
   * soft     nofile         524280
   * hard     nofile         524280

After logging in again or otherwise reloading those limits, confirm the process
limits with ``ulimit -a`` and make sure values such as ``open files`` and
``max user processes`` match the expected settings.

This section is intentionally operational rather than prescriptive. The exact
values should be chosen for the target machine and workload, but if a large TCP
bridge deployment behaves as though connections or worker threads are capped,
operating-system limits are one of the first places to check.

What To Explore Next
====================

- Connection topology rules: :doc:`/stream_interface/connecting`
- Receive-side handling: :doc:`/stream_interface/receiving`
- ``Fifo`` usage before a bridge: :doc:`/stream_interface/fifo`
- ``RateDrop`` usage before a bridge: :doc:`/stream_interface/rate_drop`

Related Topics
==============

- Memory TCP bridge: :doc:`/memory_interface/tcp_bridge`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/stream/tcpcore`
  - :doc:`/api/python/rogue/interfaces/stream/tcpserver`
  - :doc:`/api/python/rogue/interfaces/stream/tcpclient`

- C++:

  - :doc:`/api/cpp/interfaces/stream/tcpCore`
  - :doc:`/api/cpp/interfaces/stream/tcpServer`
  - :doc:`/api/cpp/interfaces/stream/tcpClient`
