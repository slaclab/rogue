.. _interfaces_clients_simple:

=======================
Simple Client Interface
=======================

The Rogue ``SimpleClient`` is a lightweight Python client for direct access to
a running tree over the ZMQ server endpoint.

It is a good fit when you need:

* Script-friendly read/write/exec operations
* Minimal dependencies
* String-path based access without constructing a mirrored local tree

Compared to :doc:`/pyrogue_tree/client_interfaces/virtual`, ``SimpleClient``
is intentionally narrower in scope but faster to adopt in small scripts.

Basic usage
===========

.. code-block:: python

   from pyrogue.interfaces import SimpleClient

   with SimpleClient(addr='localhost', port=9099) as client:
       # Read with hardware access
       print(client.get('root.RogueVersion'))
       print(client.getDisp('root.RogueVersion'))

       # Read cached/shadow value only
       print(client.value('root.RogueVersion'))
       print(client.valueDisp('root.RogueVersion'))

       # Set values
       client.set('root.AxiVersion.ScratchPad', 0x100)
       client.setDisp('root.AxiVersion.ScratchPad', '0x100')

       # Execute a command
       client.exec('root.SomeCommand', '0x100')

Update callbacks
================

``SimpleClient`` can register a callback that is invoked for each Variable
update published by the server.

.. code-block:: python

   import time
   from pyrogue.interfaces import SimpleClient

   def on_update(path, value):
       print(f'{path} = {value}')

   with SimpleClient(addr='localhost', port=9099, cb=on_update):
       print('Monitoring updates. Press Ctrl+C to stop.')
       try:
           while True:
               time.sleep(1.0)
       except KeyboardInterrupt:
           print('Stopping monitor.')

Logging
=======

``SimpleClient`` does not expose a dedicated Python or Rogue logger.

In practice, troubleshooting usually relies on:

- Exceptions raised by failed request/reply operations
- Logging on the server side, especially :doc:`zmq_server`
- Application-level prints or Python logging around client calls

If you need richer client-side observability, :doc:`virtual` is the better
interface because it exposes a Python logger and richer mirrored-tree state.

What To Explore Next
====================

- Server-side transport setup: :doc:`/pyrogue_tree/client_interfaces/zmq_server`
- Mirrored-tree access model: :doc:`/pyrogue_tree/client_interfaces/virtual`
- CLI operations for quick checks: :doc:`/pyrogue_tree/client_interfaces/commandline`

API Reference
==============

:doc:`/api/python/interfaces_simpleclient`
