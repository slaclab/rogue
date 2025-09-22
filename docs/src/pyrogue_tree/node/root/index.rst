.. _pyrogue_tree_node_root:

====
Root
====

The Root class is the fundamental building block of the :ref:`pyrogue_tree`.
The tree hierarchy starts with a root node.


Root Class Documentation
========================

.. autoclass:: pyrogue.Root
   :members:
   :member-order: bysource
   :inherited-members:

In this example ...

Python Root Example
===================

Below is an example of creating a root which ...

.. code-block:: python

    import pyrogue

    # Create a subclass of a root 
    class MyRoot(...):

C++ Root Example
================

Below is an example of creating a root device in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a root 
   class MyRoot : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

