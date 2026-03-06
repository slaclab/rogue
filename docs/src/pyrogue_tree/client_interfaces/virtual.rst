.. _interfaces_clients_virtual:

========================
Virtual Client Interface
========================

``VirtualClient`` mirrors a running remote tree into a local client-side object
model, so client code can use familiar ``Device``/``Variable``/``Command`` access patterns.

Use ``VirtualClient`` when you need:

* Tree-like object access from the client (``client.root.Device.Var`` style)
* Richer metadata and listener behavior
* A path to prototype complex workflows in client code before moving logic into
  the server-side tree

Unlike :doc:`/pyrogue_tree/client_interfaces/simple`, ``VirtualClient`` depends
on broader Rogue/PyRogue libraries.

Basic usage
===========

.. code-block:: python

   from pyrogue.interfaces import VirtualClient

   with VirtualClient(addr='localhost', port=9099) as client:
       root = client.root

       print(root.RogueVersion.get())
       print(root.RogueVersion.valueDisp())

       root.AxiVersion.ScratchPad.set(0x100)
       root.AxiVersion.ScratchPad.setDisp('0x100')
       root.SomeCommand.exec('0x100')

Access to metadata and listeners
================================

Because the tree is mirrored, you can inspect Variable metadata and attach
listeners in the same style as server-side code.

.. code-block:: python

   from pyrogue.interfaces import VirtualClient

   with VirtualClient(addr='localhost', port=9099) as client:
       root = client.root

       print(root.AxiVersion.ScratchPad.typeStr)
       print(root.AxiVersion.ScratchPad.mode)
       print(root.AxiVersion.ScratchPad.units)

       def listener(path, varValue):
           print(f'{path} = {varValue.value}')

       root.UpTime.addListener(listener)

Waiting on Variable conditions
==============================

``VariableWait`` is useful when client logic needs to block until one or more
Variable conditions are satisfied.

.. code-block:: python

   from pyrogue.interfaces import VirtualClient, VariableWait

   with VirtualClient(addr='localhost', port=9099) as client:
       root = client.root

       # Wait until uptime exceeds 1000 seconds
       VariableWait(
           [root.AxiVersion.UpTime],
           lambda values: values[0].value > 1000,
       )


Link-state monitoring
=====================

``VirtualClient`` exposes connection state and link monitor callbacks.

.. code-block:: python

   from pyrogue.interfaces import VirtualClient

   with VirtualClient(addr='localhost', port=9099) as client:
       def link_monitor(state):
           print(f'Link state is now {state}')

       client.addLinkMonitor(link_monitor)
       print(client.linked)
       client.remLinkMonitor(link_monitor)

API reference
=============

See :doc:`/api/python/interfaces_virtualclient` for generated API details.
