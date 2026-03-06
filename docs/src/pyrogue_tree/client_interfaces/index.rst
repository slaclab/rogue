.. _pyrogue_tree_client_interfaces:
.. _interfaces_clients:
.. _pyrogue_tree_client_access:

=================
Client Interfaces
=================

PyRogue client interfaces expose a running ``Root`` to external tools for
automation, monitoring, and operations.

Most deployments use :py:class:`~pyrogue.interfaces.ZmqServer` as the server-side
transport. The server is added to the ``Root`` and clients connect over TCP.

Connection model
================

1. start the server side from your ``Root`` (typically ``ZmqServer``)
2. connect one or more clients (simple script client, virtual mirrored client,
   CLI tools, or GUI)
3. perform read/write/command operations against the same tree model

Why this matters
================

This model allows one running tree to serve multiple concurrent workflows:

* Operations GUIs
* Display GUIs
* Automation scripts
* Jupyter notebooks
* Command-line tools

Choosing an interface
=====================

Use :doc:`simple` when you want lightweight string-path access with minimal
client dependencies.

Use :doc:`virtual` when you want a mirrored tree object model with richer
metadata and listener behavior.

Use :doc:`commandline` for shell-driven checks, quick reads/writes, and PyDM
launch workflows.

Use :doc:`zmq_server` when implementing or configuring the server side in your
``Root``.

Operational notes
=================

- Treat remote command paths as part of your public control surface.
- Keep Variable naming stable to reduce client-side breakage.
- Document expected polling/update cadence for remote consumers.
- Prefer ``127.0.0.1`` for local-only deployments and explicit non-loopback
  binds for remote access.

Python interface adapters
=========================

Rogue also provides built-in Python interface adapters for stream-variable and
OS-backed integration patterns:

- :doc:`memory_stream_variable`
- :doc:`os_command_memory_slave`
- :doc:`osmemmaster`

Related API references
======================

- :doc:`/api/python/interfaces_zmqserver`
- :doc:`/api/python/interfaces_simpleclient`
- :doc:`/api/python/interfaces_virtualclient`

Minimal setup pattern
=====================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.interfaces

   class MyRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(name='MyRoot', **kwargs)

           self.zmqServer = pyrogue.interfaces.ZmqServer(
               root=self,
               addr='127.0.0.1',
               port=0,
           )
           self.addInterface(self.zmqServer)

.. toctree::
   :maxdepth: 1
   :caption: Client Interfaces:

   zmq_server
   simple
   virtual
   commandline
   memory_stream_variable
   os_command_memory_slave
   osmemmaster
