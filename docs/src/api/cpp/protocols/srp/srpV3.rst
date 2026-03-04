.. _protocols_srp_classes_srpV3:

=====
SrpV3
=====

`rogue::protocols::srp::SrpV3` bridges Rogue memory transactions to SRPv3
stream frames that are transported to hardware SRP endpoints.

For SRPv3 packet-level protocol details, see:

- https://confluence.slac.stanford.edu/x/cRmVD


SrpV3 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::srp::SrpV3Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::srp::SrpV3
   :members:
