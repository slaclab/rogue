.. _pyrogue_tree_node_command_local_command:

============
LocalCommand
============

The LocalCommand class ...

A LocalCommand is a command which does not have a 1:1 associated with a hardware element
* Used to execute a sequence instructions within software
* Can include sequences of variable writes or other command executions

LocalCommand Class Definition
=============================

.. autoclass:: pyrogue.LocalCommand
   :members:
   :member-order: bysource
   :inherited-members:

In this example ... 


Python LocalCommand Example
===========================

Below is an example of creating a LocalCommand which ...

.. code-block:: python

    import pyrogue

    # Create a subclass of a LocalCommand
    class MyLocalCommand(...):

C++ LocalCommand Example
========================

Below is an example of creating a LocalCommand device in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a LocalCommand
   class MyLocalCommand : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

