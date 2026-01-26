.. _pyrogue_tree_node_variable_remote_variable:

==============
RemoteVariable
==============

The RemoteVariable class ...
See the :ref:`pyrogue_tree_node_variable` documentation page for more information.

In this example ... 

RemoteVariable Class Documentation
==================================

.. autoclass:: pyrogue.RemoteVariable
   :members:
   :member-order: bysource
   :inherited-members:


Python RemoteVariable Example
=============================

Below is an example of creating a RemoteVariable which ...

.. code-block:: python

    import pyrogue

    # Create a subclass of a RemoteVariable
    class MyRemoteVariable(...):

C++ RemoteVariable Example
==========================

Below is an example of creating a RemoteVariable device in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a RemoteVariable 
   class MyRemoteVariable : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

