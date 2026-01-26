.. _pyrogue_tree_node_variable_link_variable:

============
LinkVariable
============

The LinkVariable class ...
See the :ref:`pyrogue_tree_node_variable` documentation page for more information.

In this example ... 

LinkVariable Class Documentation
================================

.. autoclass:: pyrogue.LinkVariable
   :members:
   :member-order: bysource
   :inherited-members:


Python LinkVariable Example
===========================

Below is an example of creating a LinkVariable which defines a unique getter and setter for a RemoteVariable.

.. code-block:: python

   import pyrogue

   # Create a remote variable that needs to pass its parameters
   my_remote_var = pyrogue.RemoteVariable(name='OT_LimitRaw', offset=0x4000, bitSize=12, bitOffset=4, hidden=True)

   # Define linkedGet and linkedSet for specialized behavior
   def getTemp(var,read):
      value = var.dependencies[0].get(read)
      return (float(value)*(503.975/4096.0)) - 273.15

   def setTemp(var, value, write):
      ivalue = int((value + 273.15)*(4096/503.975))
      var.dependencies[0].set(ivalue,write)

   # Create a Link Variable with linkedGet and linkedSet, and dependency variable list
   my_linked_var = pyrogue.LinkVariable(name='OT_Limit', units='degC', linkedGet=getTemp, linkedSet=setTemp, dependencies=[my_remote_var])



Python LinkVariable Example
===========================

Below is an example of creating a LinkVariable which ...

.. code-block:: python

    import pyrogue

    # Create a subclass of a LinkVariable

C++ LinkVariable Example
========================

Below is an example of creating a LinkVariable device in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <boost/thread.hpp>

   // Create a subclass of a LinkVariable 
   class MyLinkVariable : public rogue:: ... {
      public:

      protected:

   };

A few notes on the above examples ...

