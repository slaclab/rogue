.. _tutorial_protocol_stack:

==========================================
Build A Protocol Stack With No Hardware
==========================================

:doc:`/getting_started/index` reached registers through
``rogue.interfaces.memory.Emulate``, which stands in for a memory space
directly. Real systems rarely look like that. Between a host and a board sit
several protocol layers, each solving one problem: framing requests, recovering
from packet loss, multiplexing channels over one link.

This tutorial builds that stack in three stages, adding one layer at a time so
you can see what each contributes. Every stage runs on one machine with no
hardware and no network interface beyond loopback.

.. note::

   **No hardware required.** Rogue ships software endpoints for each protocol
   layer — most importantly ``SrpV3Emulation``, which answers register requests
   from an internal store. That lets you develop and test a complete transport
   stack before a board exists.

Prerequisites
=============

Finish :doc:`/getting_started/index` first. You should be comfortable with
``Root``, ``Device``, and ``RemoteVariable``.

Every stage below uses the same one-register device, so the only thing changing
between stages is the transport underneath it:

.. literalinclude:: examples/protocol_stack.py
   :language: python
   :pyobject: ScratchDevice

Stage 1: SRP Without A Network
==============================

**SRP** (Streaming Register Protocol) is how Rogue turns register reads and
writes into stream frames. ``SrpV3`` is the host-side master: it accepts memory
transactions from a ``Device`` and emits SRP request frames.

Something has to answer those frames. On real hardware that is firmware; here
``SrpV3Emulation`` plays the role, servicing requests from its own memory store:

.. literalinclude:: examples/protocol_stack.py
   :language: python
   :pyobject: SrpRoot

Two details matter. The ``==`` operator makes a **bi-directional** connection,
which SRP needs because every request expects a response — ``>>`` would only
wire the outbound half. And ``memBase=self._srp`` points the ``Device`` at the
SRP master rather than at a memory space, so its transactions become SRP frames.

.. code-block:: text

   ScratchPad = 0xcafebabe

The register round-trips through a real protocol implementation. No emulated
memory space is involved this time: ``Emulate`` is gone, replaced by an
endpoint that speaks SRP.

Stage 2: Cross A Process Boundary
=================================

SRP frames are still moving inside one process. The TCP bridge changes that:
``TcpServer`` exposes a local memory slave on a socket, and ``TcpClient``
forwards a ``Device``'s transactions to it.

.. literalinclude:: examples/protocol_stack.py
   :language: python
   :pyobject: TcpBridgeRoot

Note the connection direction: ``self._server >> self._sim``. The bridge is the
master here — it receives transactions from the network and drives them into the
memory slave. Writing ``<<`` raises ``TypeError``.

.. code-block:: text

   ScratchPad = 0xabcd1234

Both halves run in one process here so the example is a single file. In practice
the point of this bridge is that they need not: the server can run on an
embedded CPU next to the hardware while the client runs on a workstation. See
:doc:`/memory_interface/tcp_bridge` for the two-process form.

Stage 3: The Full Transport Stack
=================================

Real links are lossy and carry more than one kind of traffic. Three layers
handle that, and ``UdpRssiPack`` bundles them:

* **UDP** moves datagrams. Fast, and makes no delivery guarantee.
* **RSSI** adds reliability on top — sequence numbers, acknowledgements,
  retransmission. This is what makes a dropped register write recoverable.
* **Packetizer** multiplexes several logical channels over the single link, so
  register access and bulk data can share one connection.

Instantiating ``UdpRssiPack`` twice, once with ``server=True``, gives a complete
link with no firmware at either end:

.. literalinclude:: examples/protocol_stack.py
   :language: python
   :pyobject: NetworkRoot

``application(0)`` selects packetizer channel 0 and connects it to the SRP
endpoint. Other channels are free for data streams — that is the multiplexing
the packetizer provides.

RSSI performs a handshake, so the link is not usable the instant the tree
starts. Poll for it rather than guessing a sleep:

.. literalinclude:: examples/protocol_stack.py
   :language: python
   :pyobject: NetworkRoot.waitForLink

.. code-block:: text

   rssi link open: True
   ScratchPad = 0xfeedface

Running All Three
=================

.. code-block:: bash

   python3 protocol_stack.py

.. code-block:: text

   --- Stage 1: SRP over emulation
      ScratchPad = 0xcafebabe
   --- Stage 2: registers over a TCP bridge
      ScratchPad = 0xabcd1234
   --- Stage 3: registers over UDP + RSSI + packetizer
      rssi link open: True
      ScratchPad = 0xfeedface

The ``Device`` code never changed. That is the point of the layering: a
``RemoteVariable`` does not know or care whether its transactions end up in an
emulator, cross a socket, or traverse UDP with retransmission. Swapping the
transport is a change to the ``Root``, not to the register map.

Choosing A Stack
================

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Situation
     - Reasonable choice
   * - Unit tests, CI, register-map development
     - ``SrpV3`` + ``SrpV3Emulation``
   * - Hardware on an embedded CPU, control from a workstation
     - TCP bridge, or ``UdpRssiPack`` if the link is lossy
   * - Ethernet-attached FPGA
     - ``UdpRssiPack`` — the usual production choice
   * - Local PCIe or DMA hardware
     - No protocol stack; see :doc:`/built_in_modules/hardware/index`

Where To Go Next
================

* :doc:`/built_in_modules/protocols/index` — every protocol module, with
  options this tutorial did not use.
* :doc:`/built_in_modules/protocols/srp/index` — SRP versions and when each
  applies.
* :doc:`/built_in_modules/protocols/rssi/index` — RSSI tuning: buffer counts,
  timeouts, retransmission.
* :doc:`/memory_interface/index` — the transaction model underneath all of this.
* :doc:`/tutorials/commands_and_groups` — continue with commands, blocks,
  and groups.

Hardware-Based Walkthroughs
===========================

To point this stack at a real board, replace ``UdpRssiPack(server=True)`` with
actual firmware and give the client the board's IP address — the host-side code
is otherwise unchanged. See
`Simple-PGPv4-KCU105 Example <https://slaclab.github.io/Simple-PGPv4-KCU105-Example/>`_
for a complete hardware bring-up.
