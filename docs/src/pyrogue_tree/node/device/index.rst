.. _pyrogue_tree_node_device:

======
Device 
======

A Device node is a container for Variable and Commands as well as other devices
* A Device class is a sub-class of rogue::interfaces::memory::Hub

   * This allows it to serve as a memory master as well as act as a hub to other memory masters
   * Variables (and their connected Blocks) associated with hardware will have an offset relative to the
       Device base address and will use the Device's linked memory::Slave when performing register accesses
   * Added Devices which are not already associated with a memory Slave interface will inherit the base
       Device's base address and Slave interface
   * A Device can have it's own direct link to a memory Slave which is not related to parent.

Key Attributes
--------------
* Devices have the following attributes, in addition to all inherited from Node:

   * offset, address, memBase, enabled
   * enabled acts as an on/off switch for invidual devices within the tree.

Key Functions
-------------
* Sub-Devices, Variables and Commands are added using the :py:meth:`add() <pyrogue.Device.add>` method
* A special device-specific :py:meth:`addRemoteVariables <pyrogue.Device.addRemoteVariables>` method allows the creation of RemoteVariable arrays
* Hide or Unhide all variables with :py:meth:`hideVariables() <pyrogue.Device.hideVariables>`
* Optional override behavior for when a system-wide hardreset is generated - :py:meth:`hardReset() <pyrogue.Device.hardReset>`
* Optional override for soft resets - :py:meth:`softReset() <pyrogue.Device.softReset>`
* Optional override for countReset - :py:meth:`countReset() <pyrogue.Device.countReset>`

Device Read/Write Operations
----------------------------

When system wide config, write and read operations are generated the blocks in each Device are manipulated by the top level Root node
* In a bulk config the shadow values in each variable are written by issuing the :py:meth:`setDisp() <pyrogue.Variable.setDisp>`
 call of each variable with the value contained in the configuration file

   * A write() transaction in each block is then generated and added to the queue
   * A verify() transaction in each block is then generated and added to the queue
   * The system then waits for the previous two transactions in each block to complete and then checks the result. Updated variables are then notified.

* In a bulk read operation:

   * A read() transaction in each block is then generated and added to the queue
   * The system then waits for the read transaction in each block to complete and then checks the result.

Similarly individual variable writes (from epcis, a GUI or a script) will result in transactions occurring on each Block

* A variable set(write=True) issues the following sequence:

   * set() the value to the variable
   * Issue a write to the associated Block
   * Issue a verify to the associated Block
   * Check the result of the transactions and generate updates.

* A variable get(read=True) issues the following sequence:

   * Issue a read from the associated block
   * Check the result of the transaction
   * Return the updated value and generate updates. 

* In some special Devices this above order may not work. Some Devices may require a special command sequence to be issued before
 and/or after each write or read transaction.
* The Device class allows the user to override the Device level functions that are called during these read and write operations.

Custom Read/Write Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Write Transaction - :py:meth:`writeBlocks() <pyrogue.Device.writeBlocks>`
* Verify Transaction - :py:meth:`verifyBlocks() <pyrogue.Device.verifyBlocks>`
* Read Transation - :py:meth:`readBlocks() <pyrogue.Device.readBlocks>`
* Wait on the result of multiple transations - :py:meth:`checkBlocks() <pyrogue.Device.checkBlocks>`

.. code-block:: python
   def writeBlocks(self, force=False, recurse=True, variable=None):
      # Do something before transation
      super(writeBlocks, self)(recurse=recurse, variable=variable)
      # Do something after transation

   def verifyBlocks(self, recurse=True, variable=None):
      # Do something before transation
      super(verifyBlocks, self)(recurse=recurse, variable=variable)
      # Do something after transation

   def readBlocks(self, recurse=True, variable=None):
      # Do something before transation
      super(readBlocks, self)(recurse=recurse, variable=variable)
      # Do something after transation

   def checkBlocks(self, recurse=True, variable=None):
      # Do something before transation
      super(checkBlocks, self)(recurse=recurse, variable=variable)
      # Do something after transation

In this example ... 

Device Class Documentation
==========================

.. autoclass:: pyrogue.Device
   :members:
   :member-order: bysource
   :inherited-members:


Python Device Example
=====================

Below is an example of creating a Device which ...

.. code-block:: python

    import pyrogue

    # Create a subclass of a Device 
    class MyDevice(...):

C++ Device Example
==================

Below is an example of creating a Device class in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a Device 
   class MyDevice : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

