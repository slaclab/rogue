.. _protocols_srp_classes_srpV0:

=====
SrpV0
=====

`rogue::protocols::srp::SrpV0` bridges Rogue memory transactions to SRPv0
stream frames that are transported to hardware SRP endpoints.
For conceptual guidance, see :doc:`/protocols/srp/srpV0`.

For SRPv0 packet-level protocol details, see:

- Https://confluence.slac.stanford.edu/x/aRmVD

Threading and locking summary
=============================

- ``doTransaction()`` and ``acceptFrame()`` may run in different contexts.
- In-flight map access is managed by base memory-slave synchronization.
- Per-transaction payload access is guarded via transaction locking.

SrpV0 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::srp::SrpV0Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::srp::SrpV0
   :members:
