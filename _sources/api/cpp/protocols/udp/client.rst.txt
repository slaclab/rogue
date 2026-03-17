.. _protocols_udp_classes_client:

======
Client
======

``Client`` is the outbound UDP endpoint class that maps stream frames to
datagrams and inbound datagrams to stream frames. This page is reference-only;
for deployment patterns see :doc:`/built_in_modules/protocols/udp/client`.

Python binding
--------------

This C++ class is also exported into Python as ``rogue.protocols.udp.Client``.

Python API page:
- :doc:`/api/python/rogue/protocols/udp/client`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::udp::ClientPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::udp::Client
   :members:
