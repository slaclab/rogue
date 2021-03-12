.. _interfaces:

==========
Interfaces
==========

Rogue is defined by a set of interfaces, both external and internal. External
interfaces include methods to access the Rogue tree from outside elements
including client scripts, GUIs and higher level DAQ systems.

The internal Rogue interfaces serve as the glue between many modules within Rogue.
These internal interfaces are designed so that once they are connected together, they
interact directly without requiring interaction with the Python layer.

For Example two C++ based stream modules can be "glued" together
with a Python script and then move data at high rates using only low level C++
threads.

The flexibility of this interface allows Stream and Memory modules to be first
prototyped in Python and then re-implemented in C++ for performance.

.. toctree::
   :maxdepth: 1
   :caption: Interfaces:

   clients/index
   stream/index
   memory/index
   simulation/index
   sql.rst

