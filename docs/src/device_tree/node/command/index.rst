.. _device_tree_node_command:

=======
Command 
=======

The Command class ...

In this example ... 

Python Command Example
======================

Below is an example of creating a command which ...

.. code-block:: python

    import pyrogue

    # Create a subclass of a command 
    class MyCommand(...):

C++ Command Example
===================

Below is an example of creating a command device in C++.

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
   :caption: Types Of Commands In The Device Tree:

   local_command/index
   remote_command/index

