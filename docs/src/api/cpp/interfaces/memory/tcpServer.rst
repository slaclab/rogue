.. _interfaces_memory_tcp_server:

=========
TcpServer
=========

For conceptual guidance on memory transport usage, see:

- :doc:`/memory_interface/index`
- :doc:`/memory_interface/tcp_bridge`

Python binding
--------------

This C++ class is also exported into Python as ``rogue.interfaces.memory.TcpServer``.

Python API page:
- :doc:`/api/python/interfaces_memory_tcpserver`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::TcpServerPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::TcpServer
   :members:
