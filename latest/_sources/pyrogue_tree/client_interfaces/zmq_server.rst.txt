.. _interfaces_python_zmqserver:

================
Python ZMQServer
================

The :py:class:`~pyrogue.interfaces.ZmqServer` interface exposes a running
PyRogue ``Root`` tree to external client programs over ZeroMQ sockets carried on
TCP. In practice, this is the primary remote-control path used by tools such
as PyDM GUIs, :ref:`interfaces_clients_simple`, and
:ref:`interfaces_clients_virtual`.

What It Provides
================

At startup, the server binds three TCP-backed ZeroMQ endpoints using a base
port:

* ``base``: publish socket for asynchronous variable updates
* ``base+1``: binary request/reply path (used by full-featured clients)
* ``base+2``: string request/reply path (used by lightweight clients)

From the client perspective, this gives access to the same tree content
available inside the Root process: read/write Variables, execute Commands, and
monitor value updates.

Common Usage Pattern
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

Client Access Examples
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

Logging
=======

There are two separate behaviors here:

- Transport logging from the underlying C++ ZMQ server
- Startup/help text printed by the Python wrapper

For transport logging, enable the Rogue C++ logger:

- Logger name: ``pyrogue.ZmqServer``
- Unified Logging API:
  ``pyrogue.setLogLevel('pyrogue.ZmqServer', 'DEBUG')``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.ZmqServer', rogue.Logging.Debug)``

Example:

.. code-block:: python

   import logging
   import pyrogue
   import pyrogue.interfaces

   pyrogue.setUnifiedLogging(True)
   pyrogue.setLogLevel('pyrogue.ZmqServer', 'DEBUG')
   server = pyrogue.interfaces.ZmqServer(root=root, addr='127.0.0.1', port=9099)

That enables the C++ transport logger. Separately, ``ZmqServer._start()``
prints the selected ports and example client commands to stdout. Those startup
messages are not controlled by the logging API.

Client-side request/retry logging comes from ``pyrogue.ZmqClient`` rather than
``ZmqServer``. During long waits, that logging is intentionally throttled:

- one warning when the client first enters the retry loop
- periodic "still waiting" warnings at a lower cadence
- one recovery message when the response arrives

This keeps long but valid transactions visible without generating a warning
every socket-timeout interval.

Related Topics
==============

- Lightweight scripting client: :doc:`/pyrogue_tree/client_interfaces/simple`
- Mirrored tree client: :doc:`/pyrogue_tree/client_interfaces/virtual`
- CLI/PyDM entry path: :doc:`/pyrogue_tree/client_interfaces/commandline`

API Reference
=============

See :doc:`/api/python/pyrogue/interfaces/zmqserver` for generated API details.
