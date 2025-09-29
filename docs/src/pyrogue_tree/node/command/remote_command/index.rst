.. _pyrogue_tree_node_command_remote_command:

=============
RemoteCommand
=============

The RemoteCommand class ...

In this example ... 

RemoteCommand Class Definition
==============================

.. autoclass:: pyrogue.RemoteCommand
   :members:
   :member-order: bysource
   :inherited-members:


Python RemoteCommand Example
============================

Below is an example of creating a RemoteCommand which ...

.. code-block:: python

   import pyrogue
      # Create a subclass of a command
      self.add(pyrogue.RemoteCommand(
         name = 'CountReset',
         offset = 0x00,
         bitSize = 1,
         bitOffset = 0,
         function = pr.BaseCommand.toggle,
      ))

      self.add(pyrouge.RemoteCommand(
         name = "ResetRx",
         offset = 0x04,
         bitSize = 1,
         bitOffset = 0,
         function = pr.BaseCommand.toggle,
      ))

.. code-block:: python

    import pyrogue

    # Create a subclass of a RemoteCommand
    class MyRemoteCommand(...):

C++ RemoteCommand Example
=========================

Below is an example of creating a RemoteCommand device in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a RemoteCommand
   class MyRemoteCommand : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

