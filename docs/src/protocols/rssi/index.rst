.. _protocols_rssi:

=============
RSSI Protocol
=============

RSSI (Reliable Streaming Service Interface) provides reliable, in-order stream
delivery over lower layers that are not inherently reliable (for example UDP).
Rogue's RSSI implementation uses sequence/acknowledge exchange, retransmission,
timeout handling, and negotiated link parameters to maintain a stable stream.
Conceptually, RSSI is based on the Reliable Data Protocol lineage defined by
RFC 908 and RFC 1151.

Protocol documentation
======================

* RSSI protocol reference: https://confluence.slac.stanford.edu/x/1IyfD
* Additional SLAC RSSI notes: https://confluence.slac.stanford.edu/x/xovOCw

The protocol reference links to the relevant RFC background used by RSSI's
reliability model (sequencing, acknowledgments, retransmission, and timeout
behavior).

How RSSI classes fit together
=============================

The ``rogue::protocols::rssi`` classes are layered as follows:

* ``Client`` / ``Server``:
  convenience wrappers that instantiate and wire the full stack for each role.
* ``Controller``:
  the protocol state machine; performs handshake, negotiation, ACK handling,
  retransmission policy, and flow-control decisions.
* ``Transport``:
  lower stream edge carrying RSSI frames to/from the underlying transport link.
* ``Application``:
  upper stream edge carrying payload frames to/from application protocols.
* ``Header``:
  helper codec/container for parsing and encoding RSSI frame headers.

Typical stream topology:

.. code-block:: text

   [Underlying link] <-> Transport <-> Controller <-> Application <-> [Upper protocol]

Python usage example
====================

In most PyRogue applications, RSSI links are created with
``pyrogue.protocols.UdpRssiPack``. This helper bundles UDP socket transport,
RSSI protocol endpoints, and packetizer wiring into a single object. It is
implemented as a ``pyrogue.Device``, so RSSI link/status variables are exposed
directly in the PyRogue tree. For wrapper details, see
:ref:`protocols_network`. For typical FPGA-facing links, instantiate it in
client mode (``server=False``).

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols
   import rogue.protocols.srp

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot')

           self.add(pyrogue.protocols.UdpRssiPack(
               name='Net',
               server=False,
               host='10.0.0.5',
               port=8192,
               jumbo=True,
               packVer=2,
               enSsi=True,
           ))
           self.addInterface(self.Net)

           srp = rogue.protocols.srp.SrpV3()
           self.Net.application(dest=0) == srp

           # Example device using SRP as memBase
           # self.add(MyDevice(name='Dev', offset=0x0, memBase=srp))

For advanced debugging or custom wiring, you can still instantiate each layer
explicitly. The following pattern is used in wrappers such as
``python/pyrogue/protocols/_Network.py``:

.. code-block:: python

   import rogue.protocols.udp
   import rogue.protocols.rssi
   import rogue.protocols.packetizer

   # Server side
   s_udp = rogue.protocols.udp.Server(0, True)
   s_rssi = rogue.protocols.rssi.Server(s_udp.maxPayload() - 8)
   s_pack = rogue.protocols.packetizer.CoreV2(True, True, True)

   s_udp == s_rssi.transport()
   s_rssi.application() == s_pack.transport()

   # Client side
   c_udp = rogue.protocols.udp.Client("127.0.0.1", s_udp.getPort(), True)
   c_rssi = rogue.protocols.rssi.Client(c_udp.maxPayload() - 8)
   c_pack = rogue.protocols.packetizer.CoreV2(True, True, True)

   c_udp == c_rssi.transport()
   c_rssi.application() == c_pack.transport()

   # Start RSSI state machines (Python binding names)
   s_rssi._start()
   c_rssi._start()

See also
========

* :ref:`protocols_network`

C++ API details for RSSI protocol classes are documented in
:doc:`/api/cpp/protocols/rssi/index`.

.. toctree::
   :maxdepth: 1
   :caption: RSSI Protocol

   client
   server
