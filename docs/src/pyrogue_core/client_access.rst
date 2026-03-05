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

Connection model
================

1. Application starts a tree rooted at ``Root``.
2. A server-side interface (commonly ZMQ) exposes the tree endpoints.
3. Clients connect and perform reads, writes, and command operations.
4. GUI and automation tools share the same conceptual access path.

Choosing a client interface
===========================

- Use Simple Client for direct scripting and operator workflows.
- Use Virtual Client when you need a local proxy object model.
- Use PyDM integration when building monitoring/control panels.

Operational notes
=================

- Treat remote command paths as part of your public control surface.
- Keep variable naming stable to reduce client-side breakage.
- Document expected polling/update cadence for remote consumers.

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
