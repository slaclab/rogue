.. _interfaces_stream_tcp_core:

TcpCore
=======

The TcpCore serves as the base class for the :ref:`interfaces_stream_tcp_server` and :ref:`interfaces_stream_tcp_client` objects whch form the two ends of a TCP stream bridge. This bridge allows bi-directional stream traffic to
flow over a TCP network interface. The server listems for connections from a client. Once the connection is formed 
the TcpClient and TcpServer serve as both stream :ref:`interfaces_stream_slave` and :ref:`interfaces_stream_master`
interfaces.

The TcpCore class generates log entries with the path: "pyrogue.stream.TcpCore"

Examples of using a TCP stream bridge are described in :ref:`interfaces_stream_using_tcp`.

TcpCore objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::stream::TcpCorePtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::stream::TcpCore
   :members:


