.. _protocols_srp_srpV3:

======================
SRP Protocol Version 3
======================

`SrpV3` converts Rogue memory transactions into SRPv3 stream frames and decodes
responses from hardware. In a typical system, those SRP frames are carried over
Rogue stream transports and terminate at FPGA/ASIC SRP logic that performs
register access.

Rogue does not re-document the SRPv3 wire format here. Use the protocol
specification for packet-level details:

- SRPv3 reference: https://confluence.slac.stanford.edu/x/cRmVD

Implementation notes
--------------------

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

Threading and locking model
---------------------------

- ``doTransaction()`` and ``acceptFrame()`` can be invoked from different
  runtime contexts.
- In-flight transaction matching is protected by the base memory-slave mutex.
- Per-transaction payload/state access is protected via ``TransactionLock``.

Integration references
----------------------

- :doc:`/memory_interface/tcp_bridge`
- :doc:`/built_in_modules/hardware/dma/stream`

Logging
-------

``SrpV3`` uses Rogue C++ logging, not Python ``logging``.

- Logger name: ``pyrogue.SrpV3``
- Unified Logging API:
  ``logging.getLogger('pyrogue.SrpV3').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.SrpV3', rogue.Logging.Debug)``
- Typical messages: transmitted request headers, received response headers,
  undersized frames, bad headers, error tails, and transaction-ID mismatches

Python usage examples
---------------------

The most common PyRogue pattern is to construct the transport and ``SrpV3``
inside a ``Root`` subclass, then pass the SRP object as ``memBase`` when adding
devices.

Root + Device(memBase=srp) with AXI Stream DMA
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

           # Stream transport carrying SRPv3 frames (register channel).
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

Related docs
------------

- :doc:`/built_in_modules/protocols/srp/index`
- C++ API: :doc:`/api/cpp/protocols/srp/srpV3`
- SRPv0 comparison: :doc:`srpV0`
- Command-only path: :doc:`cmd`
