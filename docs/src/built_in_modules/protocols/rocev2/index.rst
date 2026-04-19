.. _protocols_rocev2:
.. _built_in_modules_protocols_rocev2:

================
RoCEv2 Protocol
================

``rogue.protocols.rocev2`` is the C++/ibverbs-backed receive server for RDMA
over Converged Ethernet v2 (RoCEv2). ``Core`` opens an ibverbs device and
allocates a shared Protection Domain (PD); ``Server`` creates the Completion
Queue, Queue Pair (type ``IBV_QPT_RC``), and Memory Region, then polls for
incoming RDMA WRITEs and forwards them as Rogue stream frames.

The user-facing entry point is ``pyrogue.protocols.RoCEv2Server`` — a
``pyrogue.Device`` wrapper that owns the C++ server and the surf-side
``RoceEngine`` register block. It manages the QP handshake with the FPGA,
exposes 15 ``LocalVariable`` status/configuration fields, and integrates
cleanly into the standard PyRogue device tree via ``Root.addInterface()``.

Where RoCEv2 Fits In The Stack
==============================

Typical protocol stack:

.. code-block:: text

   FPGA RoceEngine (surf) <-> RoCEv2 NIC <-> RoCEv2Server (C++ ibverbs + Python wrapper)
                                                   |
                                           Rogue stream graph (channels via getChannel())

The FPGA side runs a ``surf.ethernet.roce._RoceEngine.RoceEngine`` block that
drives a metadata bus. ``RoCEv2Server`` reads QP parameters from that metadata
bus during ``_start()`` to complete the RC connection setup. Once the QP
reaches ``IBV_QPS_RTS``, the FPGA issues RDMA WRITEs directly into the host
Memory Region and the C++ completion-queue polling thread reassembles frames
for the Rogue stream graph.

Key Classes
===========

- ``rogue.protocols.rocev2.Core``: opens the ibverbs device and allocates the
  shared Protection Domain (PD).

- ``rogue.protocols.rocev2.Server``: inherits ``Core`` plus stream ``Master``
  and ``Slave``. Owns the Completion Queue (CQ), Queue Pair (QP, type
  ``IBV_QPT_RC``), and Memory Region (MR), runs the RX completion-queue
  polling thread, and re-posts receive work requests as frames are returned
  by downstream consumers (zero-copy slab).

- ``pyrogue.protocols.RoCEv2Server``: the PyRogue ``Device`` wrapper. Adds the
  ``RoceEngine`` child device (from ``surf.ethernet.roce._RoceEngine``) and 15
  ``LocalVariable`` fields for status and configuration.

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

The RoCEv2 server defaults to a 9000-byte maximum payload per RDMA WRITE
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

surf RoceEngine dependency
---------------------------

``RoCEv2Server`` constructs a child device of type
``surf.ethernet.roce._RoceEngine.RoceEngine`` to drive the FPGA-side
metadata-bus handshake. The ``surf`` Python package MUST be on the
Python path. Pass ``roceEngine=<existing instance>`` if your tree
already instantiates the engine elsewhere; otherwise pass
``roceEngineOffset`` and ``roceMemBase`` so ``RoCEv2Server`` can build
its own.

Python Example
==============

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols
   import rogue.protocols.srp

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot')

           # SRP memBase for the RoceEngine register block
           srp = rogue.protocols.srp.SrpV3()

           self.add(pyrogue.protocols.RoCEv2Server(
               name             = 'RoCEv2',
               ip               = '10.0.0.1',     # FPGA IP
               deviceName       = 'rxe0',          # SoftRoCE or 'mlx5_0'
               ibPort           = 1,
               gidIndex         = 0,
               maxPayload       = 9000,            # jumbo-frame MTU
               rxQueueDepth     = 256,
               roceEngineOffset = 0x00000000,
               roceMemBase      = srp,
           ))
           self.addInterface(self.RoCEv2)

           # Channel-filtered view (channel id = immediate value bits [7:0])
           data_ch = self.RoCEv2.getChannel(0)

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
