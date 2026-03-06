.. _interfaces_python_zmqserver:

================
Python ZMQServer
================

The :py:class:`pyrogue.interfaces.ZmqServer` interface exposes a running
PyRogue ``Root`` tree to external client programs over ZeroMQ sockets carried on
TCP. In practice, this is the primary remote-control path used by tools such
as PyDM GUIs, :ref:`interfaces_clients_simple`, and
:ref:`interfaces_clients_virtual`.

What it provides
================

At startup, the server binds three TCP-backed ZeroMQ endpoints using a base
port:

* ``base``: publish socket for asynchronous variable updates
* ``base+1``: binary request/reply path (used by full-featured clients)
* ``base+2``: string request/reply path (used by lightweight clients)

From the client perspective, this gives access to the same tree content
available inside the Root process: read/write Variables, execute Commands, and
monitor value updates.

Common usage pattern
====================

Create the server in ``Root.__init__`` and register it as an interface:

.. code-block:: python

   import pyrogue

   class MyRoot(pyrogue.Root):
       def __init__(self):
           super().__init__(name='Root', description='Example')

           # Expose this root over TCP/ZeroMQ.
           # port=0 enables automatic base-port selection.
           self.zmqServer = pyrogue.interfaces.ZmqServer(
               root=self,
               addr='127.0.0.1',
               port=0,
           )
           self.addInterface(self.zmqServer)

Notes
=====

* ``addr='127.0.0.1'`` keeps access local to the host.
* ``addr='*'`` binds all interfaces.
* ``port=0`` auto-selects an available base port (starting near ``9099``).
* Group filtering can be applied with ``incGroups``/``excGroups`` to control
  which Variable updates are published.
* After ``root.start()``, inspect the selected port range with
``root.zmqServer.port()`` and ``root.zmqServer.address``.

Client access examples
======================

Simple client (lightweight, string operations):

.. code-block:: python

   from pyrogue.interfaces import SimpleClient

   with SimpleClient(addr='127.0.0.1', port=9099) as client:
       print(client.getDisp('root.RogueVersion'))
       client.setDisp('root.AxiVersion.ScratchPad', '0x100')
       print(client.valueDisp('root.AxiVersion.ScratchPad'))

Virtual client (mirrored remote tree):

.. code-block:: python

   from pyrogue.interfaces import VirtualClient

   with VirtualClient(addr='127.0.0.1', port=9099) as client:
       root = client.root
       print(root.RogueVersion.valueDisp())
       root.AxiVersion.ScratchPad.set(0x100)



Class API
=========

See :doc:`/api/python/interfaces_zmqserver` for generated API details.
