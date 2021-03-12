.. _interfaces_clients_virtual:

========================
Virtual Client Interface
========================

The Rogue VirtualClient class provides a powerfull client interface to a running Rogue
tree. The VirtualClient is designed to fully replicate the Rogue tree in the client,
providing the same level of access to Rogue nodes as is available inside the core Rogue
python code. Variables, Commands and even the Root classes are fully mirrored in the
client, supporting access to the same methods and attributes as defined in the Rogue
tree API.

This allows functions and other sequences of Rogue operations to exist either in the client
or core Rogue tree, enabling complex functions to be first developed in a client script
using the VirtualClient and then inserted into the Rogue core.

Unlike the :ref:`interfaces_clients_simple` which operates as a standalone class, the Virtual
client uses much of the Rogue libraries and requires a full Rogue installation to operate.

Below is an example of using the VirtualClient in a python script:

.. code-block:: python

   with VirtualClient(addr="localhost",port=9099) as client:

      # Get the reference to the root node
      root = client.root

      # Get a variable value with a read, this returns the native value
      ret = root.RogueVersion.get()
      print(f"Version = {ret}")

      # Get the string representation a variable value with a read
      ret = root.RogueVersion.disp()
      print(f"Version = {ret}")

      # Get a variable value without a read, this returns the native value
      ret = root.RogueVersion.value()
      print(f"Version = {ret}")

      # Get the string representation a variable value without a read
      ret = root.RogueVersion.valueDisp()
      print(f"Version = {ret}")

      # Set a variable value using the native value
      root.AxiVersion.Scratchpad.set(0x100)

      # Set a variable value using the string representation of the value
      root.AxiVersion.ScratchPad.setDisp("0x100")

      # Execute a command with an optional argument, passing either the native or string value
      root.SomeCommand.exec("0x100")


Unlike the SimpleClient the VirtualClient provides access to all of the attributes to the Rogue classes:

.. code-block:: python

   print(f"Type  = {root.AxiVersion.ScratchPad.typeStr}")
   print(f"Mode  = {root.AxiVersion.ScratchPad.mode}")
   print(f"Units = {root.AxiVersion.ScratchPad.units}")
   print(f"Min   = {root.AxiVersion.ScratchPad.minimum}")
   print(f"Max   = {root.AxiVersion.ScratchPad.maximum}")

Update callbacks can be attached to a Variable as in the Rogue tree:

.. code-block:: python

   def listener(path,varValue):
      print(f"{path} = {varValue.value}")

   root.UpTime.addListener(listener)

The VariableWait helper function can also be used.

.. code-block:: python

   # Wait for the uptime to be greater than 1000 seconds
   VariableWait(root.AxiVersion.UpTime, lambda varValues: varValues['root.UpTime'].value > 1000)

The VirtualClient maintains a connection to the Rogue core. The status of this connection
can be directly accessed through the linked attribute. Additionally a callback function
can be added to be called any time the link state changes.

.. code-block:: python

   # create a callback function to be notified of link state changes
   def linkMonitor(state):
      print(f"Link state is now {state}")

   # Add a link monitor
   client.addLinkMonitor(linkMonitor)

   # Remove a link monitor
   client.remLinkMonitor(linkMonitor)

   # Get the current link state
   print(f"Current link state is {client.linked}")


VirtualClient Description
=========================

The class description for the VirtualClient class is included below:

.. autoclass:: pyrogue.interfaces.VirtualClient
   :members:
   :member-order: bysource

