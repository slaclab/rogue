.. _pyrogue_tree_root_client_access:
.. _pyrogue_tree_client_access:

===================
Client Connectivity
===================

PyRogue exposes tree access using built-in client/server interfaces attached at
the ``Root`` boundary.

Rogue provides a mechanism for remote clients to access a running PyRogue tree
over network interfaces. This includes script interfaces, command-line
interfaces, and the PyDM-based Rogue GUI.

Primary interfaces
==================

- ZMQ server: :doc:`/pyrogue_tree/client_interfaces/zmq_server`
- Simple client: :doc:`/pyrogue_tree/client_interfaces/simple`
- Virtual client: :doc:`/pyrogue_tree/client_interfaces/virtual`

Connection model
================

1. Application starts a tree rooted at ``Root``.
2. A server-side interface (commonly ZMQ) exposes tree endpoints.
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
- Keep Variable naming stable to reduce client-side breakage.
- Document expected polling/update cadence for remote consumers.

Python interface adapters
=========================

Rogue also provides built-in Python interface adapters for stream-variable and
OS-backed integration patterns:

- :doc:`/pyrogue_core/python_interfaces/memory_stream_variable`
- :doc:`/pyrogue_core/python_interfaces/os_command_memory_slave`
- :doc:`/pyrogue_core/python_interfaces/osmemmaster`

Related API references
======================

- :doc:`/api/python/interfaces_zmqserver`
- :doc:`/api/python/interfaces_simpleclient`
- :doc:`/api/python/interfaces_virtualclient`
