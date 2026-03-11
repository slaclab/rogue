.. _protocols_srp_srpV0:

======================
SRP Protocol Version 0
======================

`SrpV0` converts Rogue memory transactions into SRPv0 stream frames and decodes
responses from hardware. In a typical system, those SRP frames are carried over
Rogue stream transports and terminate at FPGA/ASIC SRP logic that performs
register access.

Rogue does not re-document the SRPv0 wire format here. Use the protocol
specification for packet-level details:

- SRPv0 reference: https://confluence.slac.stanford.edu/x/aRmVD

Implementation notes
--------------------

- Rogue can issue multiple SRPv0 requests before responses return; these are
  tracked as in-flight transactions by transaction ID.
- Responses are matched by ID, so response order does not need to match request
  order.
- If a response is missing, the initiating memory master times out based on the
  configured software timeout (see ``Master.setTimeout()``, microseconds).
- Late responses that arrive after timeout are treated as expired and ignored.
- ``SrpV0`` enforces 4-byte alignment and defaults to a 2048-byte max
  transaction size (from constructor ``memory::Slave(4, 2048)``).

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

``SrpV0`` uses Rogue C++ logging, not Python ``logging``.

- Logger name: ``pyrogue.SrpV0``
- Configuration API:
  ``rogue.Logging.setFilter('pyrogue.SrpV0', rogue.Logging.Debug)``
- Typical messages: transmitted request headers, received response headers,
  undersized frames, bad headers, expired transactions, and error tails

Set the filter before constructing the ``SrpV0`` object. Rogue C++ loggers
copy their level when the logger instance is created.

Python usage example
--------------------

The common PyRogue pattern is to construct the transport and ``SrpV0`` inside a
``Root`` subclass, then pass the SRP object as ``memBase`` when adding devices.

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

           # Stream transport carrying SRPv0 frames (register channel).
           self.regStream = rogue.hardware.axi.AxiStreamDma(dev, 0, True)

           # SRPv0 protocol bridge.
           self.srp = rogue.protocols.srp.SrpV0()

           # Bidirectional stream connection: transport <-> SRPv0.
           self.regStream == self.srp

           # Attach register map device to SRPv0 memory slave interface.
           self.add(MyRegs(
               name='Regs',
               offset=0x00000000,
               memBase=self.srp,
               expand=True,
           ))

Related Topics
--------------

- :doc:`/built_in_modules/protocols/srp/index`
- Preferred newer protocol: :doc:`srpV3`
- Command-only path: :doc:`cmd`

API Reference
-------------

- Python: :doc:`/api/python/rogue/protocols/srp_srpv0`
- C++: :doc:`/api/cpp/protocols/srp/srpV0`
