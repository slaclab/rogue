.. _interfaces_stream_tcp_client:

TcpClient
=========

The TcpClient is a sub-class of :ref:`interfaces_stream_tcp_core` which operates the core
in client mode. The client connects to a server at the defined address and port combination.

Examples of using a TCP stream bridge are described in :ref:`interfaces_stream_using_tcp`.

TcpClient objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::TcpClientPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::TcpClient
   :members:

