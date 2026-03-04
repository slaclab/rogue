.. _protocols_srp_classes_srpV0:

=====
SrpV0
=====

`rogue::protocols::srp::SrpV0` bridges Rogue memory transactions to SRPv0
stream frames that are transported to hardware SRP endpoints.

For SRPv0 packet-level protocol details, see:

- https://confluence.slac.stanford.edu/x/aRmVD


SrpV0 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::srp::SrpV0Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::srp::SrpV0
   :members:
