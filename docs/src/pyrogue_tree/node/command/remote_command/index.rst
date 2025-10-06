.. _pyrogue_tree_node_command_remote_command:

=============
RemoteCommand
=============

The RemoteCommand class ...

A RemoteCommand is a command which has a 1:1 associated with a hardware element

* Subclass of RemoteVariable
* Used to generate a set of writes to the associated hardware element

A number of commonly used commands and sequence generators are provided to support RemoteCommand operations.
These functions can generally be grouped into two categories:

* True functions, which will perform simple operations.
* Function creators, which return another function when called.

See the class documentation for :py:class:`Base Command <pyrogue.BaseCommand>` or :py:class:`Remote Command <pyrogue.RemoteCommand>`
for more information on these functions.

Python RemoteCommand Examples
=============================

Basic Usage
-----------
.. code-block:: python

   import pyrogue

   command = RemoteCommand(
      name='demo', description='', value=None, 
      disp='{}', enum=None, minimum=None,
      maximum=None, base=pyrogue.UInt, 
      offset=None, bitSize=32, 
      bitOffset=0, function=None)

Important things to note:

* Passed attributes are the same as for BaseCommand and RemoteVariable
* Value is optionally used to set an initial value in the underlying Block
* Base is used to determine the arg type

Below is an example of creating a RemoteCommand which ...

.. code-block:: python

   import pyrogue
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


RemoteCommand Class Definition
==============================

.. autoclass:: pyrogue.RemoteCommand
   :members:
   :member-order: bysource
   :inherited-members:


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

