.. _protocols_srp_srpV3:

======================
SRP Protocol Version 3
======================

For current SRP register links, Rogue provides
``rogue.protocols.srp.SrpV3``. ``SrpV3`` converts Rogue memory transactions
into SRPv3 stream frames and decodes hardware responses back into memory
transaction completion.

Rogue does not re-document the SRPv3 wire format here. Use the protocol
specification for packet-level details:

- SRPv3 reference: https://confluence.slac.stanford.edu/x/cRmVD

When To Use ``SrpV3``
=====================

- Use for current systems unless endpoint compatibility requires :doc:`srpV0`.
- Use when the link needs SRP register semantics rather than raw commands.
- Pair it with a stream transport such as DMA or UDP/RSSI/packetizer.

Behavior
========

- Rogue can issue multiple SRPv3 requests before responses return; these are
  tracked as in-flight transactions by transaction ID.
- Responses are matched by ID, so response order does not need to match request
  order.
- If a response is missing, the initiating memory master times out based on the
  configured software timeout (see ``Master.setTimeout()``, microseconds).
- Late responses that arrive after timeout are treated as expired and ignored.
- SRPv3 also carries a hardware timeout field in the request header
  (C++: ``setHardwareTimeout()``, Python binding: ``_setHardwareTimeout()``),
  which is separate from Rogue software wait
  timeout handling.
- ``SrpV3`` enforces 4-byte alignment and defaults to a 4096-byte max
  transaction size (from constructor ``memory::Slave(4, 4096)``).

The class sits directly between the memory and stream interfaces. Connect it to
a lower stream transport, then use the SRP object as the ``memBase`` for
PyRogue devices or other memory clients.

Threading And Locking
=====================

- ``doTransaction()`` and ``acceptFrame()`` can be invoked from different
  runtime contexts.
- In-flight transaction matching is protected by the base memory-slave mutex.
- Per-transaction payload/state access is protected via ``TransactionLock``.

Logging
=======

``SrpV3`` uses Rogue C++ logging.

- Logger name: ``pyrogue.SrpV3``
- Unified Logging API:
  ``logging.getLogger('pyrogue.SrpV3').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.SrpV3', rogue.Logging.Debug)``
- Typical messages: transmitted request headers, received response headers,
  undersized frames, bad headers, error tails, and transaction-ID mismatches

Set the filter before constructing the ``SrpV3`` object. Rogue C++ loggers
copy their level when the logger instance is created.

Python Example
==============

The most common PyRogue pattern is to construct the transport and ``SrpV3``
inside a ``Root`` subclass, then pass the SRP object as ``memBase`` when adding
devices.

.. code-block:: python

   import pyrogue as pr
   import rogue.hardware.axi
   import rogue.protocols.srp

   class MyRegs(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='ScratchPad',
               description='Example RW register',
               offset=0x0000,
               bitSize=32,
               mode='RW',
               base=pr.UInt,
           ))

   class MyRoot(pr.Root):
       def __init__(self, dev='/dev/datadev_0', **kwargs):
           super().__init__(timeout=2.0, **kwargs)

           # Stream transport carrying SRPv3 frames.
           self.regStream = rogue.hardware.axi.AxiStreamDma(dev, 0, True)

           # SRPv3 protocol bridge.
           self.srp = rogue.protocols.srp.SrpV3()

           # Bidirectional stream connection: transport <-> SRPv3.
           self.regStream == self.srp

           # Optional protocol timeout field encoded into SRPv3 header.
           self.srp._setHardwareTimeout(0x0A)  # Python binding name.

           # Attach register map device to SRPv3 memory slave interface.
           self.add(MyRegs(
               name='Regs',
               offset=0x00000000,
               memBase=self.srp,
               expand=True,
           ))

Related Topics
==============

- :doc:`/memory_interface/tcp_bridge`
- :doc:`/built_in_modules/hardware/dma/stream`
- :doc:`/built_in_modules/protocols/srp/index`
- SRPv0 comparison: :doc:`srpV0`
- Command-only path: :doc:`cmd`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/srp/srpv3`
- C++: :doc:`/api/cpp/protocols/srp/srpV3`
