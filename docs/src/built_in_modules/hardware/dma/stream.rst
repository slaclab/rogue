.. _hardware_axi_stream:
.. _hardware_axi_features:

============
AxiStreamDma
============

For connecting Rogue stream graphs directly to FPGA DMA channels, Rogue
provides ``rogue.hardware.axi.AxiStreamDma``. This class wraps
``aes-stream-drivers`` DMA channels as Rogue stream interfaces, so hardware
channels can participate in ordinary Rogue stream topologies with the usual
``>>``, ``<<``, and ``==`` connection semantics.

The underlying driver stack is:
`slaclab/aes-stream-drivers <https://github.com/slaclab/aes-stream-drivers>`_.
That repository is useful reference material when you need to understand the
driver-visible DMA buffer model, channel reservation mask, or lower-level AXI
stream helper APIs.

The common use case is a PCIe or SoC-backed design where one firmware stream
destination needs to appear in software as a Rogue transport endpoint. Hardware
that commonly uses this pattern includes PCIe cards, Zynq-based platforms, and
other designs built around the AXI DMA driver stack.

A single ``AxiStreamDma`` instance is typically used for one firmware data
channel or destination path. In many designs:

- One destination carries a register protocol such as SRPv3.
- One or more other destinations carry waveform, event, or diagnostic traffic.

That makes ``AxiStreamDma`` the normal host-side boundary between the Linux
driver and the rest of the Rogue stream graph.

Key Constructor Arguments
=========================

``AxiStreamDma(path, dest, ssiEnable)``

- ``path`` is the Linux device path, commonly ``/dev/datadev_0``.
- ``dest`` selects the destination or channel value used by the driver and
  firmware path.
- ``ssiEnable`` enables SSI SOF and EOFE handling in the user fields.

Destination Mapping
===================

From the software side, ``dest`` is the value used to select which firmware DMA
path you want to open. The important practical rule is to match the value that
the firmware and driver stack expect for that stream endpoint.

In the common ``aes-stream-drivers`` convention used by Rogue:

- The low 8 bits of ``dest`` correspond to the AXI stream ``tDest`` value
- The upper bits select the lane or higher-level DMA channel path implemented
  in firmware

That means software normally treats ``dest`` as one combined routing number,
even if the firmware designer thinks of it as ``lane`` plus ``tDest``.

Examples:

- ``0x000`` means lane 0, destination 0.
- ``0x001`` means lane 0, destination 1.
- ``0x100`` means lane 1, destination 0.
- ``0x102`` means lane 1, destination 2.

You do not need a deep understanding of lanes to use ``AxiStreamDma``
correctly. The main requirement is to know which combined ``dest`` values the
firmware exports for register access, data, diagnostics, or protocol
endpoints.

Typical Uses
============

- Attach a data-producing or data-consuming firmware channel to a Rogue stream
  graph.
- Carry SRP traffic over a DMA stream destination.
- Serve as the lower transport under packetizer or other protocol layers.
- Connect a Root-managed DAQ path to file I/O, PRBS, filters, or custom stream
  endpoints.

Example: Root With Control And Data DMA Paths
=============================================

This is a common PyRogue pattern: one DMA destination carries SRPv3 register
traffic, and another carries a framed data stream that is written to disk.

.. code-block:: python

   import pyrogue as pr
   import rogue.hardware.axi as rha
   import rogue.protocols.srp as rps
   import pyrogue.utilities.fileio as puf

   class MyRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           # Example register block reached through the SRPv3 control channel.
           self.add(pr.RemoteVariable(
               name='ScratchPad',
               description='Example RW register',
               offset=0x0000,
               bitSize=32,
               mode='RW',
               base=pr.UInt,
           ))

   class BoardRoot(pr.Root):
       def __init__(self, dev='/dev/datadev_0', **kwargs):
           super().__init__(timeout=2.0, **kwargs)

           # Destination 0 is reserved for register access.
           self.regStream = rha.AxiStreamDma(dev, 0, True)
           self.srp = rps.SrpV3()

           # Bidirectional stream connection: DMA transport <-> SRPv3 bridge.
           self.regStream == self.srp

           # Optional SRPv3 protocol timeout encoded into the outbound header.
           self.srp._setHardwareTimeout(0x0A)

           # The top-level register tree talks to hardware through SRPv3.
           self.add(MyRegs(
               name='Regs',
               offset=0x00000000,
               memBase=self.srp,
               expand=True,
           ))

           # Destination 1 carries framed acquisition data.
           self.dataStream = rha.AxiStreamDma(dev, 1, True)

           # Tree-managed file writer for captured data.
           self.writer = puf.StreamWriter(name='Writer')
           self.add(self.writer)

           # Route the DMA data stream into channel 0 of the file writer.
           self.dataStream >> self.writer.getChannel(0)

           # Register both DMA interfaces so Root owns their lifecycle.
           self.addInterface(self.regStream, self.dataStream)

Example: Root-Owned DMA Processing Chain
========================================

This pattern keeps the DMA object in the ``Root`` and inserts ordinary Rogue
stream stages between the hardware channel and the final sink.

.. code-block:: python

   import pyrogue as pr
   import rogue.hardware.axi as rha
   import rogue.interfaces.stream as ris
   import pyrogue.utilities.fileio as puf

   class CaptureRoot(pr.Root):
       def __init__(self, dev='/dev/datadev_0', **kwargs):
           super().__init__(**kwargs)

           # Open the hardware data channel at destination 1.
           self.dataDma = rha.AxiStreamDma(dev, 1, True)

           # Buffer short bursts from hardware before writing to disk.
           self.fifo = ris.Fifo(100, 0, False)

           # Optional debug tap. Attach it after the primary path so frame
           # allocation still follows the main processing chain.
           self.debug = ris.Slave()
           self.debug.setDebug(64, 'DMA Debug')

           # Tree-managed file writer.
           self.writer = puf.StreamWriter(name='Writer')
           self.add(self.writer)

           # Primary capture path: DMA -> FIFO -> file writer.
           self.dataDma >> self.fifo >> self.writer.getChannel(0)

           # Secondary branch for console debugging.
           self.dataDma >> self.debug

           # Root manages the DMA lifecycle.
           self.addInterface(self.dataDma)

Example: Transport Tuning
=========================

These controls are usually added after the basic path is working and you need
to diagnose driver behavior or tune a platform-specific setup.

.. code-block:: python

   import rogue.hardware.axi as rha

   # Disable zero-copy before constructing any DMA object for this device path.
   rha.AxiStreamDma.zeroCopyDisable('/dev/datadev_0')

   dma = rha.AxiStreamDma('/dev/datadev_0', 1, True)

   # Enable kernel-driver debug messages. These usually appear in dmesg.
   dma.setDriverDebug(1)

   # Emit timeout warnings if TX or frame allocation blocks too long.
   dma.setTimeout(1500)

Threading And Lifecycle
=======================

``AxiStreamDma`` does create background activity:

- A background RX thread starts in the constructor.
- Transmit happens synchronously in ``acceptFrame()``.
- Destruction or ``_stop()`` shuts down the RX thread and closes descriptors.

In a PyRogue application, treat it as a managed interface when the Root is
responsible for startup and shutdown. In a standalone script, explicitly stop
it when the transport is no longer needed.

Common Controls
===============

- ``setTimeout(timeout)``
  Sets the TX and allocation wait timeout in microseconds.
- ``setDriverDebug(level)``
  Enables lower-level driver diagnostics, typically visible in ``dmesg``.
- ``dmaAck()``
  Sends a driver-specific DMA acknowledge pulse when the hardware design uses
  that mechanism.
- ``zeroCopyDisable(path)``
  Disables zero-copy for a device path before any instance is created on that
  path.

Zero-Copy Notes
===============

Zero-copy is enabled by default when the driver and device path support it.

In this mode, ``AxiStreamDma`` asks ``aes-stream-drivers`` to map the driver's
DMA buffers into user space, then uses those mapped buffers directly as Rogue
frame storage. That avoids an extra copy between a driver-owned DMA buffer and
a separately allocated software buffer.

The practical effect is:

- Received DMA data can be exposed to Rogue as frames without first copying
  into a second payload buffer.
- Outbound frame allocation can use DMA-backed buffers directly when the caller
  allows zero-copy allocation.
- CPU overhead and memory bandwidth are lower than in the copied path.

When zero-copy is disabled or unavailable, Rogue falls back to locally allocated
frame buffers and copies data across the DMA boundary as needed.

Disable zero-copy only when debugging, when a platform-specific constraint
requires it, or when you deliberately want to rule out buffer-mapping behavior
while isolating a problem.

If you do disable it, call ``zeroCopyDisable(path)`` before creating any
``AxiStreamDma`` object for that path.

Logging
=======

``AxiStreamDma`` uses Rogue C++ logging and also exposes a separate driver debug
path.

- Logger name: ``pyrogue.axi.AxiStreamDma``
- Unified Logging API:
  ``logging.getLogger('pyrogue.axi.AxiStreamDma').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.axi.AxiStreamDma', rogue.Logging.Debug)``
- Typical Rogue messages: DMA channel creation, send/receive timeouts, and
  errored-frame handling
- Driver debug helper: ``setDriverDebug(level)``

Enable Rogue logging before construction:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.axi.AxiStreamDma', rogue.Logging.Debug)

Driver debug usually appears in ``dmesg`` rather than in Rogue's own logger
output.

Related Topics
==============

- :doc:`/built_in_modules/hardware/dma/index`
- :doc:`/built_in_modules/hardware/dma/memory`
- :doc:`/built_in_modules/protocols/srp/index`
- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/stream_interface/index`

API Reference
=============

- Python: :doc:`/api/python/rogue/hardware/axi/axistreamdma`
- C++: :doc:`/api/cpp/hardware/axi/axiStreamDma`
