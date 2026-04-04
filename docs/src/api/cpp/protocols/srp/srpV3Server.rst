.. _protocols_srp_classes_srpV3Server:

===========
SrpV3Server
===========

`rogue::protocols::srp::SrpV3Server` is a software emulation of a hardware
SRPv3 endpoint. It accepts SRPv3 request frames and sends SRPv3 response
frames backed by an internal memory store. This module is used for CI
regression testing of the :doc:`srpV3` client module without hardware.

For conceptual guidance, see :doc:`/built_in_modules/protocols/srp/srpV3Server`.

Threading and locking summary
=============================

- ``acceptFrame()`` may run from any stream transport thread.
- Internal memory access is protected by a mutex.

Python binding
--------------

This C++ class is also exported into Python as ``rogue.protocols.srp.SrpV3Server``.

Python API page:
- :doc:`/api/python/rogue/protocols/srp/srpv3server`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::srp::SrpV3ServerPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::srp::SrpV3Server
   :members:
