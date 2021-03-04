.. _interfaces_clients_simple:

========================
Simple Client Interface
========================

The Rogue SimpleClient class is a lightweight python class which can be used on its own
with minimal dependencies, requiring only the zmq library. This file is fully portable and
can be used outside of the greater Rogue package.

The most current file can be downloaded from:

https://github.com/slaclab/rogue/blob/master/python/pyrogue/interfaces/_SimpleClient.py

Below is an example of using the SimpleClient in a python script:

.. code-block:: python

   with SimpleClient(addr="localhost",port=9099) as client:

      # Get a variable value with a read, this returns the native value
      ret = client.get("root.RogueVersion")
      print(f"Version = {ret}")

      # Get the string representation a variable value with a read
      ret = client.getDisp("root.RogueVersion")
      print(f"Version = {ret}")

      # Get a variable value without a read, this returns the native value
      ret = client.value("root.RogueVersion")
      print(f"Version = {ret}")

      # Get the string representation a variable value without a read
      ret = client.valueDisp("root.RogueVersion")
      print(f"Version = {ret}")

      # Set a variable value using the native value
      ret = client.set("root.ScratchPad",0x100)

      # Set a variable value using the string representation of the value
      ret = client.setDisp("root.ScratchPad","0x100")

      # Execute a command with an optional argument, passing either the native or string value
      ret = client.exec("root.SomeCommand","0x100")


The SimpleClient interface also provides a mechanism to provide a callback function which is
called anytime a Rogue variable is updated. The call back function is called once for each
of the updated variables reported by the Rogue server.

.. code-block:: python

   def myCallBack(path,value):
      print(f"Got updated value for {path} = {value}")


   with SimpleClient(addr="localhost",port=9099,cb=myCallBack) as client:

      # Any variale updates received while this interface is activate will
      # be passed to the myCallBack function


The class description for the SimpleClient class is included below:

.. automodule:: pyrogue.interfaces.SimpleClient
   :members:

