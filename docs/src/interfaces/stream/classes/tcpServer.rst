.. _interfaces_stream_tcp_server:

TcpServer
=========

The TcpServer is a sub-class of :ref:`interfaces_stream_tcp_core` which operates the core
in server mode. The server listens for connections from a client to form a stream bridge.

Examples of using a TCP stream bridge are described in :ref:`interfaces_stream_using_tcp`.

TcpServer objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::TcpServerPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::TcpServer
   :members:

