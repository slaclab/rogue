.. _hardware_axi:

=========================
AXI DMA Driver Wrappers
=========================

For host-side access to FPGA DMA channels and register space through the
``aes-stream-drivers`` stack, Rogue provides driver wrappers in
``rogue.hardware.axi``.

The underlying Linux driver and user-space support library live in
`slaclab/aes-stream-drivers <https://github.com/slaclab/aes-stream-drivers>`_.
That repository is the right lower-level reference when you need driver API
details such as DMA buffer mapping, channel reservation masks, or register-path
behavior.

These wrappers are usually the software boundary between the Linux driver and
the rest of a Rogue application:

- ``AxiStreamDma`` turns one DMA stream channel into Rogue stream interfaces.
- ``AxiMemMap`` turns the driver register path into a Rogue memory interface.

Higher-level protocols such as SRP, RSSI, or packetizer are layered on top of
these wrappers when the firmware design expects them.

Subtopics
=========

- :doc:`stream`
  Use ``AxiStreamDma`` for framed data channels.
- :doc:`memory`
  Use ``AxiMemMap`` for register and memory transactions exposed through the
  driver path.

Typical Integration Pattern
===========================

Most applications split the work between one register path and one or more
stream paths. The register side is usually exposed as a Rogue memory endpoint,
while the data side is connected into a Rogue stream graph and then layered
with SRP, packetizer, file I/O, or custom processing only where the firmware
actually uses those protocols.

1. Use :doc:`memory` when firmware registers should appear as a Rogue memory
   endpoint.
2. Use :doc:`stream` when firmware data channels should participate in a Rogue
   stream graph.
3. Add higher-level protocol layers above those wrappers only when the firmware
   path actually uses them.

Related Topics
==============

- :doc:`/built_in_modules/protocols/srp/index`
- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/memory_interface/index`
- :doc:`/stream_interface/index`

.. toctree::
   :maxdepth: 1
   :caption: AXI Hardware

   stream
   memory
