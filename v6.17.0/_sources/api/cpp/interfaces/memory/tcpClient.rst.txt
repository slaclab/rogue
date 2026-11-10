.. _interfaces_memory_tcp_client:

=========
TcpClient
=========

For conceptual guidance on memory transport usage, see:

- :doc:`/memory_interface/index`
- :doc:`/memory_interface/tcp_bridge`

Python binding
--------------

This C++ class is also exported into Python as ``rogue.interfaces.memory.TcpClient``.

Python API page:
- :doc:`/api/python/rogue/interfaces/memory/tcpclient`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::TcpClientPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::TcpClient
   :members:
