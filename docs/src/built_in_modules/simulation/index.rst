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

Available components
====================

- ``MemEmulate``: in-memory memory-slave emulator for register/device testing
- ``Pgp2bSim``: simulated PGP2B endpoint with VC stream links and sideband
- ``SideBandSim``: standalone sideband socket bridge for opcode/remote-data

These helpers are implemented in Python in
``python/pyrogue/interfaces/simulation.py``.

What To Explore Next
====================

- Memory emulation patterns: :doc:`/built_in_modules/simulation/mememulate`
- Simulated PGP2B links: :doc:`/built_in_modules/simulation/pgp2b`
- Sideband-only workflows: :doc:`/built_in_modules/simulation/sideband`
- Memory transaction model details: :doc:`/memory_interface/index`
- Stream connection patterns: :doc:`/stream_interface/connecting`

.. toctree::
   :maxdepth: 1
   :caption: Simulation:

   mememulate
   pgp2b
   sideband
