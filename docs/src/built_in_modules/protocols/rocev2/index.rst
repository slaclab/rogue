.. _protocols_rocev2:
.. _built_in_modules_protocols_rocev2:

================
RoCEv2 Protocol
================

``rogue.protocols.rocev2`` is the C++/ibverbs-backed receive server for RDMA
over Converged Ethernet v2 (RoCEv2). ``Core`` opens an ibverbs device and
allocates a shared Protection Domain (PD); ``Server`` creates the Completion
Queue, Queue Pair (type ``IBV_QPT_RC``), and Memory Region, then polls for
incoming RDMA SENDs and forwards them as Rogue stream frames.

The user-facing entry point is ``pyrogue.protocols.RoCEv2Server`` — a
``pyrogue.Device`` wrapper that owns the C++ server. It exposes 15
``LocalVariable`` status/configuration fields and integrates cleanly into
the standard PyRogue device tree via ``Root.addInterface()``. The FPGA-side
QP handshake is driven by the surf ``RoCEv2Engine`` device (a separate node
in the tree, not a child of the server); the application ``Root`` sequences
the host↔FPGA bring-up and teardown.

Where RoCEv2 Fits In The Stack
==============================

Typical protocol stack:

.. code-block:: text

   FPGA RoceEngine (surf) <-> RoCEv2 NIC <-> RoCEv2Server (C++ ibverbs + Python wrapper)
                                                   |
                                           Rogue stream graph (channels via getChannel())

The FPGA side runs a ``surf.ethernet.roce.RoCEv2Engine`` block that drives a
metadata bus. The application ``Root`` reads the host QP parameters from
``RoCEv2Server`` (``getHostParams``), runs ``engine.setupConnection()`` over
that metadata bus, and finishes the host side with
``server.completeConnection()``. Once the QP reaches ``IBV_QPS_RTS``, the FPGA
issues RDMA-SEND-with-immediate frames that land in the host's pre-posted
receive slots and the C++ completion-queue polling thread reassembles frames
for the Rogue stream graph. Because RDMA-SEND is two-sided, the host receive
queue itself is the flow-control mechanism: when it drains, the NIC RNR-NAKs
the FPGA, which self-throttles to the poll thread's re-post rate.

Key Classes
===========

- ``rogue.protocols.rocev2.Core``: opens the ibverbs device and allocates the
  shared Protection Domain (PD).

- ``rogue.protocols.rocev2.Server``: inherits ``Core`` plus stream ``Master``
  and ``Slave``. Owns the Completion Queue (CQ), Queue Pair (QP, type
  ``IBV_QPT_RC``), and Memory Region (MR), runs the RX completion-queue
  polling thread, and re-posts receive work requests as frames are returned
  by downstream consumers (zero-copy slab).

- ``pyrogue.protocols.RoCEv2Server``: the PyRogue ``Device`` wrapper around
  the C++ server. Exposes 15 ``LocalVariable`` fields for status and
  configuration. The FPGA-side ``surf.ethernet.roce.RoCEv2Engine`` is a
  separate tree node (not a child of the server); the ``Root`` drives the
  handshake between the two.

When To Use
===========

- You are talking to a RoCEv2-capable FPGA (e.g. the
  Simple-10GbE-RUDP-KCU105-Example ``RoceEngine`` block).
- You need higher throughput than UDP+RSSI provides on a 10/25/100 GbE link.
- You have a host NIC that supports RoCEv2 (Mellanox/NVIDIA ``mlx5_*``) or you
  are developing against SoftRoCE (``rxe0``).

Operational Requirements
========================

Jumbo-frame MTU (9000 bytes)
-----------------------------

The RoCEv2 server defaults to a 9000-byte maximum payload per RDMA SEND
(``DefaultMaxPayload`` in ``include/rogue/protocols/rocev2/Core.h``). The
host NIC and every switch in the path MUST be configured for a 9000-byte
(or larger) MTU — typically:

.. code-block:: bash

   # Host NIC (replace with your interface)
   sudo ip link set dev enp1s0f0 mtu 9000

If any hop along the path uses a 1500-byte MTU, the FPGA will see RDMA
WRITEs silently dropped or NACK'd. There is no graceful auto-fallback.

SoftRoCE (rxe) development workflow
-------------------------------------

For development without a RoCEv2 NIC, use the in-kernel ``rdma_rxe``
SoftRoCE driver. On Debian/Ubuntu install ``rdma-core`` and load the
module:

.. code-block:: bash

   sudo apt install rdma-core ibverbs-utils
   sudo modprobe rdma_rxe
   sudo rdma link add rxe0 type rxe netdev <ifname>
   ibv_devices    # confirm rxe0 appears

Then pass ``deviceName='rxe0'`` to ``RoCEv2Server``. SoftRoCE works for
functional bring-up and CI but does not deliver the throughput of a
hardware RoCEv2 NIC.

surf RoCEv2Engine dependency
----------------------------

The FPGA-side metadata-bus handshake is performed by
``surf.ethernet.roce.RoCEv2Engine``, instantiated as part of the FPGA
register tree (e.g. under ``Core`` in the application device map), NOT by
``RoCEv2Server``. The application ``Root`` wires the two together:
``engine.setupConnection(**server.getHostParams())`` followed by
``server.completeConnection(...)``. The ``surf`` Python package MUST be on
the Python path for the engine device.

Python Example
==============

The application ``Root`` owns both the host ``RoCEv2Server`` and the FPGA
``surf.ethernet.roce.RoCEv2Engine`` register block, and sequences the
host↔FPGA QP bring-up inside its own ``start()``. The two configuration
dataclasses are passed in at construction: ``RoCEv2ServerCfg`` carries the
host-NIC knobs, and a single ``RoCEv2TransportCfg`` is forwarded into BOTH
``engine.setupConnection()`` and ``server.completeConnection()`` so the FPGA
and host sides cannot drift on ``pmtu`` / ``minRnrTimer``.

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols
   from pyrogue.protocols import (
       RoCEv2Server, RoCEv2ServerCfg, RoCEv2TransportCfg,
   )

   class MyRoot(pr.Root):
       def __init__(self, *, rocev2Cfg, transportCfg, **kwargs):
           super().__init__(name='MyRoot', **kwargs)

           self._transportCfg = transportCfg

           # FPGA register tree (carries surf.ethernet.roce.RoCEv2Engine).
           self.add(MyFpgaCore(name='Core', memBase=...))

           # The host-side RX server. The FPGA-side RoCEv2Engine is a
           # separate node (self.Core.RoCEv2Engine), not a child of the server.
           self.add(RoCEv2Server(name='RoCEv2', rocev2Cfg=rocev2Cfg))
           self.addInterface(self.RoCEv2)

       def start(self, **kwargs):
           super().start(**kwargs)

           # Drive the host<->FPGA QP handshake once transport is up.
           server = self.RoCEv2
           engine = self.Core.RoCEv2Engine          # surf.ethernet.roce.RoCEv2Engine
           xport  = self._transportCfg

           # Host params (hostQpn/hostRqPsn/hostSqPsn/mrAddr/mrLen) feed the FPGA;
           # the engine returns a RoCEv2FpgaParams (fpgaQpn/lkey/...) to finish
           # the host side.
           params = server.getHostParams()
           fpga = engine.setupConnection(
               **params._asdict(),
               pmtu        = xport.pmtu,
               minRnrTimer = xport.minRnrTimer,
               rnrRetry    = xport.rnrRetry,
               retryCount  = xport.retryCount,
           )
           server.completeConnection(
               fpga.fpgaQpn,
               fpgaLkey    = fpga.lkey,
               pmtu        = xport.pmtu,
               minRnrTimer = xport.minRnrTimer,
               rnrRetry    = xport.rnrRetry,
               retryCount  = xport.retryCount,
           )
           server.printConnInfo()

   # Construct with the two cfg bundles (mirrors rocev2PrbsTest.py):
   root = MyRoot(
       rocev2Cfg = RoCEv2ServerCfg(
           ip         = '192.168.2.10',   # FPGA IP
           deviceName = 'mlx5_0',          # HW NIC ('rxe0' for SoftRoCE)
           gidIndex   = -1,                # auto-detect the RoCE v2 IPv4 GID
       ),
       transportCfg = RoCEv2TransportCfg(  # proven acceptance-gate defaults
           minRnrTimer = 12,
       ),
   )
   with root:
       # Root.start() already ran the bring-up; the QP is connected here.
       # Channel-filtered view (channel id = immediate value bits [7:0]).
       data_ch = root.RoCEv2.getChannel(0)

Logging
=======

RoCEv2 protocol-state logging is emitted by the C++ server and the PyRogue
wrapper via Rogue logging.

Logger names:

- C++ core/server loggers (created via ``rogue::Logging::create``):

  - ``rocev2.Core``
  - ``rocev2.Server``

- PyRogue wrapper loggers are created via ``pyrogue.logInit`` and follow
  the ``pyrogue.<family>.<ClassName>.<path>`` pattern. ``RoCEv2Server``
  is a ``pyrogue.Device``, so its logger is:

  - ``pyrogue.Device.RoCEv2Server.<path>``

  For the example above (``name='RoCEv2'`` inside ``MyRoot``), the
  wrapper logger is ``pyrogue.Device.RoCEv2Server.MyRoot.RoCEv2``.

- Unified Logging API examples:

  - ``pyrogue.setLogLevel('rocev2.Server', 'DEBUG')``
  - ``pyrogue.setLogLevel('pyrogue.Device.RoCEv2Server.MyRoot.RoCEv2', 'DEBUG')``

- Legacy Logging API example:

  - ``rogue.Logging.setFilter('rocev2.Server', rogue.Logging.Debug)``

These loggers are most useful when debugging QP bring-up, metadata-bus
handshake failures, and RC connection state transitions.

Troubleshooting
===============

Stale FPGA resources after a crash
-------------------------------------

If a previous session crashed or was killed without a clean ``Root.stop()``,
the FPGA RoCEv2 engine may still hold a PD, MR, or QP from that session.
The next ``engine.setupConnection()`` call (driven by the ``Root`` during
``start()``) will fail with a ``rogue.GeneralError`` whose message includes:

.. code-block:: text

   FPGA PD allocation failed — the FPGA RoCEv2 engine likely has stale
   resources from a previous session that crashed without a clean teardown.
   Reprogram the FPGA bitfile to reset its state.

The same guidance appears for MR and QP allocation failures. The firmware
provides no way to enumerate existing resources without knowing the QPN in
advance, so a reprogram is the only reliable recovery path.

MR length exceeds 32-bit metadata-bus field
---------------------------------------------

The FPGA-side Memory Region length is ``maxPayload * rxQueueDepth``. If this
product is too large for the 32-bit ``length`` field of the metadata bus, the
surf ``RoCEv2Engine.setupConnection()`` argument validation raises a
``rogue.GeneralError`` before any bus traffic, so the FPGA is never left with
a partially-allocated resource. The default configuration
(``maxPayload=9000``, ``rxQueueDepth=256``, product ~2.3 MB) is far below this
limit; the guard protects against accidentally passing very large queue depths.

QP state-machine enforcement
-------------------------------

The metadata-bus codec now lives in surf
(``surf.ethernet.roce._RoCEv2Protocol``). Its encoders are stateless — they
encode and send any QP transition without checking whether it is valid. The
**FPGA state machine is the single source of truth**: illegal transitions
return ``success=False``, which ``RoCEv2Engine.setupConnection()`` raises as a
``rogue.GeneralError`` on the setup path and logs as a warning on the
``teardownConnection()`` path. No Python-side state mirror is maintained
because it would become stale after a crash and block legitimate teardown
attempts.

Related Topics
==============

- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`/built_in_modules/protocols/srp/index`
- :doc:`/stream_interface/index`
- :doc:`/memory_interface/index`

API Reference
=============

- C++: :doc:`/api/cpp/protocols/rocev2/index`
- Python (Boost.Python exports):
  :doc:`/api/python/rogue/protocols/rocev2/core`
  :doc:`/api/python/rogue/protocols/rocev2/server`
- Python (PyRogue wrapper): :doc:`/api/python/pyrogue/protocols/rocev2`
