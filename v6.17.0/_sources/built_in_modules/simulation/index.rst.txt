.. _interfaces_simulation:

====================
Simulation Utilities
====================

Rogue simulation utilities provide fast software-only stand-ins for common
hardware and link behaviors.

They are most useful for:

- Local development without connected hardware
- Deterministic protocol bring-up and integration testing
- Fault-injection workflows (for example dropped memory transactions)

Available Components
====================

- ``MemEmulate``: in-memory memory-slave emulator for register/device testing
- ``Pgp2bSim``: simulated PGP2B endpoint with VC stream links and sideband
- ``SideBandSim``: standalone sideband socket bridge for opcode/remote-data

Selection Guidance
==================

- Use ``MemEmulate`` when validating memory-transaction behavior (read/write,
  verify, and retry flows) without hardware.
- Use ``Pgp2bSim`` when testing multi-VC stream links and paired sideband
  behavior together.
- Use ``SideBandSim`` when testing sideband control/data paths without hardware.

Related Topics
==============

- Memory emulation patterns: :doc:`/built_in_modules/simulation/mememulate`
- Simulated PGP2B links: :doc:`/built_in_modules/simulation/pgp2b`
- Memory transaction model details: :doc:`/memory_interface/index`
- Stream connection patterns: :doc:`/stream_interface/connecting`

.. toctree::
   :maxdepth: 1
   :caption: Simulation:

   mememulate
   pgp2b
