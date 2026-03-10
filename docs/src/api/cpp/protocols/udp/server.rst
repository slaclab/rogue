.. _protocols_udp_classes_server:

======
Server
======

``Server`` is the UDP bind/listen endpoint class and supports querying the
active bound port via ``getPort()``. This page is reference-only; for usage
patterns see :doc:`/built_in_modules/protocols/udp/server`.

Python binding
--------------

This C++ class is also exported into Python as ``rogue.protocols.udp.Server``.

Python API page:
- :doc:`/api/python/protocols_udp_server`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::udp::ServerPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::udp::Server
   :members:
