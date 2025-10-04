.. _pyrogue_tree_node_command:

=======
Command 
=======

The Command class ...

A Command :ref:`Node <pyrogue_tree_node>` is the management interface for executing commands within the system.

* Types of Commands

   * BaseCommand - abstract base class for the other Command classes
   * LocalCommand - command without 1-1 to hardware element
   * RemoteCommand - command with 1-1 to hardware element

      * RemoteCommand is also a sub-class of Remote Variable

* All commands are sub-classes of :ref:`BaseVariable <pyrogue_tree_node_variable>` and support all variable attributes

* A command has a :py:pyrogue:`function <pyrogue.BaseCommand.function>` which is called when the command is executed

   * Has a set of supported args which are optional and detected by the variable
   * Names must match the template to be matched
   * C++ functions exposed through python are supported but no args are passed

* Commands can either be executed directly or with the :py:pyrogue:`call <pyrogue.BaseCommand.call>` method:

   * command(arg)
   * command.call(arg)

BaseCommand
===========

The BaseCommand class is the parent class for all child Command Types. Click the following
links for more information on the subtypes.

.. toctree::
   :maxdepth: 1
   :caption: Types of Commands in the PyRogue Tree:

   local_command/index
   remote_command/index

BaseCommand Class Documentation
===============================

This is the breakdown of the BaseCommand class, which is the parent class of all Commands.
Inherits from BaseVariable class

.. autoclass:: pyrogue.BaseCommand
   :members:
   :member-order: bysource
   :inherited-members:

In this example ... 

Python Command Example
======================

Below is an example of creating a Command which ...

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

