.. _pyrogue_tree_node_command:

=======
Command 
=======

The Command class ...

In this example ... 


This is the breakdown of the BaseCommand class, which is the parent class of all Commands.
Inherits from BaseVariable class 

.. autoclass:: pyrogue.BaseCommand
   :members:
   :member-order: bysource

Python Command Example
======================

Below is an example of creating a Command which ...


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

    # Create a subclass of a command 
    class MyCommand(...):

C++ Command Example
===================

Below is an example of creating a Command device in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a command 
   class MyCommand : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

.. toctree::
   :maxdepth: 1
   :caption: Types Of Commands In The PyRogue Tree:

   local_command/index
   remote_command/index

