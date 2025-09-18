.. _pyrogue_tree_node_variable:

========
Variable
========

The BaseVariable class is the parent class for all child Variable Types. Click the following
links for more information on the subtypes.

.. toctree::
   :maxdepth: 1
   :caption: Types of Variables in the PyRogue Tree:

   link_variable/index
   local_variable/index
   remote_variable/index


BaseVariable Class Documentation
================================

.. autoclass:: pyrogue.BaseVariable
   :members:
   :member-order: bysource


Python Variable Example
=======================

Below is an example of creating a Variable which ...

.. code-block:: python

    import pyrogue

    # Create a subclass of a Variable 
    class MyVariable(...):

C++ Variable Example
====================

Below is an example of creating a Variable device in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a Variable 
   class MyVariable : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...
