.. _pyrogue_core_client_access:

===================
Client Connectivity
===================

PyRogue exposes tree access using built-in client/server interfaces.

Rogue provides a mechanism for remote clients to access a PyRogue tree over a
network interface. This includes script interfaces, command-line interfaces,
and the PyDM-based Rogue GUI.

This page is now the canonical conceptual home for client connectivity
guidance. Legacy narrative remains available at
:doc:`/interfaces/clients/index`.

Primary interfaces:

- ZMQ server: :doc:`/interfaces/pyrogue/zmq_server`
- Simple client: :doc:`/interfaces/clients/simple`
- Virtual client: :doc:`/interfaces/clients/virtual`

Python interface adapters
=========================

Rogue also provides built-in Python interface adapters for stream-variable and
OS-backed integration patterns:

- :doc:`/interfaces/pyrogue/memory_stream_variable`
- :doc:`/interfaces/pyrogue/os_command_memory_slave`
- :doc:`/interfaces/pyrogue/osmemmaster`

Related API reference:

- :doc:`/api/python/interfaces_zmqserver`
- :doc:`/api/python/interfaces_simpleclient`
- :doc:`/api/python/interfaces_virtualclient`
