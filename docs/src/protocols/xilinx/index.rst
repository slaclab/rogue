.. _protocols_xilinx:

================
Xilinx Protocols
================

Rogue Xilinx protocol support provides an XVC bridge for JTAG-over-TCP workflows
such as FPGA debug through Vivado hardware manager. In practice, this is used to
connect to an on-chip ILA (ChipScope) through firmware that exposes an
AxisToJtag-style endpoint.

Rogue sits between a TCP XVC client and the hardware JTAG endpoint:

- Upstream side: XVC TCP connection (tool-facing).
- Downstream side: Rogue stream transport (hardware-facing), such as rUDP, PGP,
  or other stream-capable links.

At a high level:

- ``Xvc`` hosts the XVC TCP server and translates XVC requests into JTAG
  operations over Rogue streams.
- ``JtagDriver`` implements protocol framing/retry/query logic and defines the
  transport transfer contract.
- ``XvcServer`` and ``XvcConnection`` manage connection accept/command parsing
  for XVC TCP clients.

The XVC bridge is typically connected to a bidirectional Rogue stream path to
hardware firmware that implements the corresponding JTAG bridge endpoint.

When to use this stack
----------------------

- You need remote JTAG/ILA access from Vivado over TCP.
- Your firmware exposes an AxisToJtag-compatible endpoint.
- Rogue is already the integration layer for the transport path.

Typical usage
-------------

1. Create an ``Xvc`` instance on a local TCP port.
2. Connect it bidirectionally to a Rogue stream transport path to hardware.
3. Start the XVC server thread.
4. Connect Vivado/XVC client to the local TCP port.

Python example
--------------

.. code-block:: python

   import pyrogue as pr
   import rogue.hardware.axi
   import rogue.protocols.xilinx

   class JtagRoot(pr.Root):
       def __init__(self, dev='/dev/datadev_0', jtagDest=2, xvcPort=2542, **kwargs):
           super().__init__(**kwargs)

           # Stream path to firmware JTAG bridge endpoint.
           self.jtagStream = rogue.hardware.axi.AxiStreamDma(dev, jtagDest, True)

           # XVC TCP bridge (localhost:xvcPort).
           self.xvc = rogue.protocols.xilinx.Xvc(xvcPort)

           # Bidirectional stream connection.
           self.jtagStream == self.xvc

           # Register interfaces for start/stop.
           self.addInterface(self.jtagStream, self.xvc)


C++ example
-----------

.. code-block:: cpp

   #include <rogue/hardware/axi/AxiStreamDma.h>
   #include <rogue/protocols/xilinx/Xvc.h>

   int main() {
       auto jtagStream = rogue::hardware::axi::AxiStreamDma::create("/dev/datadev_0", 2, true);
       auto xvc        = rogue::protocols::xilinx::Xvc::create(2542);

       *jtagStream == xvc;

       xvc->start();
       // Application loop...
       xvc->stop();
       return 0;
   }

JtagDriver notes
----------------

``JtagDriver`` is the protocol/transport abstraction used by ``Xvc``. It can
also be subclassed directly in C++ for custom transports:

- Subclass implements raw transfer primitive (``xfer``)
- Subclass reports transport vector limit (``getMaxVectorSize``)
- Base class handles protocol framing, retries, query, and vector chunking

Threading and Lifecycle
-----------------------

- ``Xvc`` runs a background server thread for TCP XVC clients.
- Incoming Rogue reply frames are queued for synchronous consumption by
  ``Xvc::xfer()``.
- ``Xvc`` uses an internal mutex around response-buffer copy paths.
- Implements Managed Interface Lifecycle:
  :ref:`pyrogue_tree_node_device_managed_interfaces`

API references
--------------

C++ API reference pages are collected in :doc:`/api/cpp/protocols/xilinx/index`:

- :doc:`/api/cpp/protocols/xilinx/xvc`
- :doc:`/api/cpp/protocols/xilinx/jtagDriver`
- :doc:`/api/cpp/protocols/xilinx/xvcServer`
- :doc:`/api/cpp/protocols/xilinx/xvcConnection`
