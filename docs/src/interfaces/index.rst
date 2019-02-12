.. _interfaces:

Interfaces
==========

Rogue is built around a series of interfaces which serve as the glue
between many modules within Rogue. The interfaces are designed so that once they are 
connected together, they interact directly without requiring interaction with
the Python layer. For Example two C++ based stream modules can be "glued" together
with a Python script and then move data at high rates usuing only low level C++
threads. This of course is not the case when one of the two end points is written in
Python. The flexibility of this interface allows Stream and Memory modules to be first
prototyped in Python and then re-implemented in C++ for performance.

.. toctree::
   :maxdepth: 1
   :caption: Interfaces:

   stream/index
   memory/index

