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

Connection Model
================

1. Start the server side from your ``Root`` (typically ``ZmqServer``)
2. Connect one or more clients (simple script client, virtual mirrored client,
   CLI tools, or GUI)
3. Perform read/write/command operations against the same tree model

Why This Matters
================

This model allows one running tree to serve multiple concurrent workflows:

* Operations GUIs
* Display GUIs
* Automation scripts
* Jupyter notebooks
* Command-line tools

Choosing An Interface
=====================

Use :doc:`simple` when you want lightweight string-path access with minimal
client dependencies.

Use :doc:`virtual` when you want a mirrored tree object model with richer
metadata and listener behavior.

Use :doc:`commandline` for shell-driven checks, quick reads/writes, and PyDM
launch workflows.

Use :doc:`zmq_server` when implementing or configuring the server side in your
``Root``.

Operational Notes
=================

- Treat remote command paths as part of your public control surface.
- Keep Variable naming stable to reduce client-side breakage.
- Document expected polling/update cadence for remote consumers.
- Prefer ``127.0.0.1`` for local-only deployments and explicit non-loopback
  binds for remote access.

API Reference
======================

- :doc:`/api/python/pyrogue/interfaces/zmqserver`
- :doc:`/api/python/pyrogue/interfaces/simpleclient`
- :doc:`/api/python/pyrogue/interfaces/virtualclient`

Minimal Setup Pattern
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

Related Topics
==============

- Server configuration details: :doc:`/pyrogue_tree/client_interfaces/zmq_server`
- Lightweight scripting access: :doc:`/pyrogue_tree/client_interfaces/simple`
- Mirrored-tree client workflows: :doc:`/pyrogue_tree/client_interfaces/virtual`
- Shell and GUI entry points: :doc:`/pyrogue_tree/client_interfaces/commandline`

.. toctree::
   :maxdepth: 1
   :caption: Client Interfaces:

   zmq_server
   simple
   virtual
   commandline
