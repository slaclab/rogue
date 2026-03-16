.. _protocols_xilinx:

================
Xilinx Protocols
================

For remote JTAG and ILA access through a Rogue-managed transport, Rogue
provides ``rogue.protocols.xilinx``. The class most users actually instantiate
is ``rogue.protocols.xilinx.Xvc``, which presents a local XVC TCP server to
Vivado and forwards those XVC operations across a Rogue stream link to firmware
that implements an AxisToJtag-style endpoint.

This is the normal software-side path when Vivado Hardware Manager needs to
reach on-chip debug logic through an existing Rogue transport such as DMA, PGP,
or a network bridge.

How The Bridge Fits Together
============================

The XVC bridge sits between the tool-facing TCP connection and the
hardware-facing Rogue stream path:

.. code-block:: text

   Vivado XVC client <-> Xvc TCP server <-> Rogue stream transport <-> firmware JTAG bridge

``Xvc`` combines three roles in one object:

- A TCP XVC server for the tool-facing side.
- A Rogue ``Master``/``Slave`` pair for the hardware-facing stream path.
- The ``JtagDriver`` protocol engine that handles query, shift, retry, and
  vector chunking logic.

The lower transport can be whatever the firmware design already exposes for the
JTAG bridge path. In practice that is often a dedicated DMA destination, but it
can also be another bidirectional Rogue stream path.

When This Stack Fits
====================

- You need remote JTAG or ILA access from Vivado over TCP.
- Your firmware exposes an AxisToJtag-compatible endpoint.
- Rogue already owns the transport path to the hardware.

Key Classes
===========

- ``Xvc`` is the normal class to instantiate. It owns the local XVC listener
  and bridges XVC requests to the Rogue stream transport.
- ``JtagDriver`` is the lower-level protocol base class used by ``Xvc``. It is
  mostly relevant to C++ users implementing a custom transport.
- ``XvcServer`` and ``XvcConnection`` are support classes behind the local TCP
  listener and client session handling.

Typical Workflow
================

The normal workflow is straightforward:

1. Create an ``Xvc`` instance on a local TCP port.
2. Connect it bidirectionally to the Rogue stream path that reaches the
   firmware JTAG bridge endpoint.
3. Let a ``Root`` manage lifecycle, or start and stop the bridge explicitly in
   a standalone script.
4. Point Vivado or another XVC client at the local TCP port.

Root-Based Python Example
=========================

The most common PyRogue pattern is to create the XVC bridge in the ``Root``,
connect it to the firmware-facing transport, and register both interfaces for
managed lifecycle.

.. code-block:: python

   import pyrogue as pr
   import rogue.hardware.axi as rha
   import rogue.protocols.xilinx as rpx

   class JtagRoot(pr.Root):
       def __init__(self, dev='/dev/datadev_0', jtagDest=0x400, xvcPort=2542, **kwargs):
           super().__init__(**kwargs)

           # Open the firmware stream path that terminates at the JTAG bridge.
           # The combined destination value must match the lane and TDEST
           # implemented in firmware for the AxisToJtag endpoint.
           self.jtagStream = rha.AxiStreamDma(dev, jtagDest, True)

           # Create the local XVC server that Vivado will connect to.
           self.xvc = rpx.Xvc(xvcPort)

           # Bridge the transport path in both directions:
           #   Rogue stream <-> XVC bridge <-> Vivado TCP client
           self.jtagStream == self.xvc

           # Register both interfaces so Root owns startup and shutdown.
           self.addInterface(self.jtagStream, self.xvc)

Standalone Python Example
=========================

Without a ``Root``, the same bridge can be brought up directly in a short
script.

.. code-block:: python

   import time
   import rogue.hardware.axi as rha
   import rogue.protocols.xilinx as rpx

   # Open the stream path to the firmware JTAG bridge.
   jtag_stream = rha.AxiStreamDma('/dev/datadev_0', 0x400, True)

   # Start a local XVC server on tcp://127.0.0.1:2542.
   xvc = rpx.Xvc(2542)

   # Connect the stream transport to the XVC bridge in both directions.
   jtag_stream == xvc

   # No Root is managing lifecycle here, so start and stop explicitly.
   xvc._start()
   try:
       # Keep the process alive while Vivado connects to the local XVC port.
       while True:
           time.sleep(1.0)
   finally:
       xvc._stop()
       jtag_stream._stop()

C++ Example
===========

The same pattern applies in C++ when Rogue is being used directly without a
PyRogue ``Root``:

.. code-block:: cpp

   #include <rogue/hardware/axi/AxiStreamDma.h>
   #include <rogue/protocols/xilinx/Xvc.h>

   namespace rha = rogue::hardware::axi;
   namespace rpx = rogue::protocols::xilinx;

   int main() {
       // Open the firmware-facing stream path for the JTAG bridge endpoint.
       auto jtagStream = rha::AxiStreamDma::create("/dev/datadev_0", 0x400, true);

       // Start the local XVC server used by Vivado.
       auto xvc = rpx::Xvc::create(2542);

       // Connect the stream transport to the XVC bridge in both directions.
       *jtagStream == xvc;

       // Standalone lifecycle control in C++.
       xvc->start();

       // Application loop goes here.

       xvc->stop();
       return 0;
   }

JtagDriver Role
===============

``JtagDriver`` is the protocol and transport abstraction underneath ``Xvc``.
It is responsible for:

- Querying target capabilities.
- Framing shift and query commands.
- Applying retry logic.
- Chunking transfers to the transport-supported vector size.

For normal Python use, that detail stays behind ``Xvc``. In C++, ``JtagDriver``
can also be subclassed directly when a custom transport is needed. In that
case, the transport subclass supplies:

- ``xfer()`` to move one opaque protocol message to and from the target.
- ``getMaxVectorSize()`` to report the transport-side vector limit.

The base class then handles the protocol-level JTAG mechanics above that raw
transport primitive.

Threading And Lifecycle
=======================

``Xvc`` does create background activity:

- A background server thread accepts and services local XVC TCP clients.
- Incoming Rogue reply frames are queued for synchronous consumption by
  ``xfer()``.
- The implementation uses an internal mutex around response-buffer handling.

In Root-managed PyRogue applications, register both the transport and ``Xvc``
with ``addInterface(...)`` and let the Root manage startup and shutdown.
Without a Root, call ``_start()`` and ``_stop()`` explicitly on ``Xvc``.

Logging
=======

Xilinx support uses Rogue C++ logging:

- ``pyrogue.xilinx.xvc`` for TCP server and frame-bridge activity.
- ``pyrogue.xilinx.jtag`` for protocol-level query and shift debugging.

- Unified Logging API:
  ``logging.getLogger('pyrogue.xilinx').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.xilinx', rogue.Logging.Debug)``

You can enable the logger family before or after construction. Enable it before
construction only if you want constructor or initial server-startup messages:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.xilinx', rogue.Logging.Debug)

Related Topics
==============

- :doc:`/built_in_modules/hardware/dma/stream`
- :doc:`/stream_interface/connecting`
- :doc:`/pyrogue_tree/core/device`

API Reference
=============

- Python:
  :doc:`/api/python/rogue/protocols/xilinx/xvc`
  :doc:`/api/python/rogue/protocols/xilinx/jtagdriver`
- C++:
  :doc:`/api/cpp/protocols/xilinx/xvc`
  :doc:`/api/cpp/protocols/xilinx/jtagDriver`
  :doc:`/api/cpp/protocols/xilinx/xvcServer`
  :doc:`/api/cpp/protocols/xilinx/xvcConnection`
