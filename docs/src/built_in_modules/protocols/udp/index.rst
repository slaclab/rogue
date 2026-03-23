.. _protocols_udp:

============
UDP Protocol
============

For stream transport over IP networks, Rogue provides
``rogue.protocols.udp``. In most Rogue systems, UDP is used as the datagram
layer underneath RSSI and packetizer rather than as a standalone application
protocol.

Direct UDP-only deployment is usually limited to paths where dropped or
out-of-order packets are acceptable. For most FPGA control and data links,
UDP is just the transport substrate below RSSI, packetizer, and often SRP.

Where UDP Fits In The Stack
===========================

Typical protocol stack:

.. code-block:: text

   UDP <-> RSSI <-> Packetizer <-> Application logic

Use UDP directly only when datagram delivery semantics are acceptable for your
application. For ordered and reliable link behavior, use RSSI on top of UDP.

Key Classes
===========

The ``rogue::protocols::udp`` layer is split into:

- ``Core``:
  shared transport configuration (payload sizing, socket timeout, RX buffer
  tuning). See :doc:`/api/python/rogue/protocols/udp/core` and
  :doc:`/api/cpp/protocols/udp/core`.
- ``Client``:
  outbound endpoint to a specific remote host/port. See :doc:`client` and
  :doc:`/api/python/rogue/protocols/udp/client` and
  :doc:`/api/cpp/protocols/udp/client`.
- ``Server``:
  local bind endpoint that receives inbound datagrams and can transmit to the
  most recently observed peer. See :doc:`server` and
  :doc:`/api/python/rogue/protocols/udp/server` and
  :doc:`/api/cpp/protocols/udp/server`.

Each endpoint is both a stream ``Slave`` for outbound traffic and a stream
``Master`` for inbound traffic, so UDP objects can sit directly inside a Rogue
stream graph.

Payload Sizing And MTU
======================

``udp::Core.maxPayload()`` sets frame payload limits by MTU mode:

- Jumbo mode (``jumbo=True``): ``8972`` bytes payload
- Standard mode (``jumbo=False``): ``1472`` bytes payload

When UDP is used under RSSI, the RSSI segment size is typically derived from
the full UDP payload budget (for example ``udp.maxPayload()``). RSSI then
reserves its own 8-byte header within that segment size.

Threading And Lifecycle
=======================

- ``Client`` and ``Server`` each start a background RX thread at construction.
- C++ ``stop()`` (Python ``_stop()``) joins the thread and closes the socket.
- ``Core`` does not define a separate managed start/stop state machine.

When To Use UDP Directly
========================

- You need lightweight datagram transport over IP networks.
- Your reliability and framing requirements are handled by upper layers.
- You are integrating with existing UDP-based firmware endpoints.

When Not To Use UDP By Itself
=============================

- If you need ordered/reliable delivery semantics by default, use RSSI over
  UDP instead of raw UDP-only application flows.
- If you need transaction-level memory semantics, use SRP on top of stream
  transport rather than direct UDP framing.
- For most FPGA control/configuration links, do not deploy raw UDP-only paths;
  use RSSI (and usually packetizer/SRP) above UDP.

Python Example
==============

.. code-block:: python

   import rogue.protocols.udp
   import rogue.protocols.rssi
   import rogue.protocols.packetizer

   serv = rogue.protocols.udp.Server(0, True)
   cli = rogue.protocols.udp.Client("127.0.0.1", serv.getPort(), True)

   s_rssi = rogue.protocols.rssi.Server(serv.maxPayload())
   c_rssi = rogue.protocols.rssi.Client(cli.maxPayload())

   s_pkt = rogue.protocols.packetizer.CoreV2(True, True, True)
   c_pkt = rogue.protocols.packetizer.CoreV2(True, True, True)

   cli == c_rssi.transport()
   c_rssi.application() == c_pkt.transport()
   serv == s_rssi.transport()
   s_rssi.application() == s_pkt.transport()

C++ Example
===========

.. code-block:: cpp

   #include <rogue/protocols/udp/Client.h>
   #include <rogue/protocols/udp/Server.h>
   #include <rogue/protocols/rssi/Client.h>
   #include <rogue/protocols/rssi/Server.h>
   #include <rogue/protocols/packetizer/CoreV2.h>

   namespace rpu  = rogue::protocols::udp;
   namespace rpr  = rogue::protocols::rssi;
   namespace rpp  = rogue::protocols::packetizer;

   auto serv   = rpu::Server::create(0, true);
   auto client = rpu::Client::create("127.0.0.1", serv->getPort(), true);

   auto sRssi = rpr::Server::create(serv->maxPayload());
   auto cRssi = rpr::Client::create(client->maxPayload());

   auto sPack = rpp::CoreV2::create(true, true, true);
   auto cPack = rpp::CoreV2::create(true, true, true);

   client == cRssi->transport();
   cRssi->application() == cPack->transport();
   serv == sRssi->transport();
   sRssi->application() == sPack->transport();

Logging
=======

UDP transport uses Rogue C++ logging.

Static logger names:

- ``pyrogue.udp.Client``
- ``pyrogue.udp.Server``

Enable one side or the whole subsystem before constructing objects:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.udp', rogue.Logging.Debug)

At debug level, UDP logs socket setup and transmit/receive path events. There
is no additional runtime ``setDebug(...)`` helper on these classes.

Related Topics
==============

- :doc:`/built_in_modules/protocols/network`
- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/built_in_modules/protocols/srp/index`
- :doc:`/stream_interface/connecting`

API Reference
=============

- C++: :doc:`/api/cpp/protocols/udp/index`
- Python:
  :doc:`/api/python/rogue/protocols/udp/core`
  :doc:`/api/python/rogue/protocols/udp/client`
  :doc:`/api/python/rogue/protocols/udp/server`

.. toctree::
   :maxdepth: 1
   :caption: UDP Protocol

   client
   server
