.. _protocols_srp_srpV3Server:

============================
SRP Protocol Version 3 Server
============================

For CI regression testing of the SRPv3 protocol path, Rogue provides
``rogue.protocols.srp.SrpV3Server``. ``SrpV3Server`` emulates a hardware
SRP endpoint in software, accepting SRPv3 request frames and returning
SRPv3 response frames with an internal memory backing store.

This module is **not** intended for use with hardware. It is purely a
software construct for testing the :doc:`srpV3` client module.

When To Use ``SrpV3Server``
===========================

- Use for CI regression testing of the SRPv3 protocol path.
- Use for software-only integration tests that exercise the full SRPv3
  request/response cycle without FPGA or ASIC hardware.
- Use when developing or validating PyRogue device trees offline.

Behavior
========

- Receives SRPv3 request frames via ``acceptFrame()``.
- Decodes the 20-byte SRPv3 header (version, opcode, transaction ID,
  address, size).
- For write requests: stores payload data in internal memory.
- For read requests: returns data from internal memory (uninitialized
  memory reads as zero).
- Sends a response frame with the original header, data payload, and
  a zero status tail indicating success.
- Posted writes are processed silently with no response frame.
- Internal memory is allocated on demand in 4 KiB pages.

Connect ``SrpV3Server`` to an ``SrpV3`` client via a bidirectional stream
path using the ``==`` operator. The server acts as the remote endpoint,
completing the full protocol round-trip in software.

Threading And Locking
=====================

- ``acceptFrame()`` can be invoked from any stream transport thread.
- Internal memory access is protected by a mutex.

Logging
=======

``SrpV3Server`` uses Rogue C++ logging.

- Logger name: ``pyrogue.SrpV3Server``
- Recommended unified one-liner:
  ``pyrogue.setLogLevel('SrpV3Server', 'DEBUG')``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.SrpV3Server', rogue.Logging.Debug)``
- Typical messages: incoming request details, memory page allocations,
  response transmission, and frame validation warnings.

Python Example
==============

The typical test pattern connects ``SrpV3`` and ``SrpV3Server`` inside a
``Root`` subclass to create a software-only register access path.

.. code-block:: python

   import pyrogue as pr
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

   class TestRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(timeout=2.0, pollEn=False, **kwargs)

           # SRPv3 client (the module under test)
           self.srp = rogue.protocols.srp.SrpV3()

           # SRPv3 server (software emulation of hardware endpoint)
           self.srpServer = rogue.protocols.srp.SrpV3Server()

           # Bidirectional stream: client <-> server
           self.srp == self.srpServer

           # Attach device to SRPv3 memory interface
           self.add(MyRegs(
               name='Regs',
               offset=0x00000000,
               memBase=self.srp,
           ))

   # Usage in a test
   with TestRoot() as root:
       root.Regs.ScratchPad.set(0xDEADBEEF)
       assert root.Regs.ScratchPad.get() == 0xDEADBEEF

Related Topics
==============

- SRPv3 client: :doc:`srpV3`
- Memory emulator: :doc:`/api/python/rogue/interfaces/memory/emulate`
- SRP protocol overview: :doc:`/built_in_modules/protocols/srp/index`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/srp/srpv3server`
- C++: :doc:`/api/cpp/protocols/srp/srpV3Server`
