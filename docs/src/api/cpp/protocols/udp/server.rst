.. _protocols_udp_classes_server:

======
Server
======

``Server`` is the UDP bind/listen endpoint class and supports querying the
active bound port via ``getPort()``. This page is reference-only; for usage
patterns see :doc:`/protocols/udp/server`.

Server objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::udp::ServerPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::udp::Server
   :members:
