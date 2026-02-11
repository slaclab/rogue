.. _pyrogue_tree_node_variable_remote_variable:

==============
RemoteVariable
==============

:py:class:`pyrogue.RemoteVariable` maps a variable to hardware-accessible memory.
For example, a register in an attached FPGA
It is the standard choice for register-style control and monitoring.

Behavior
========

A RemoteVariable is defined by register mapping metadata such as:

* ``offset``
* ``bitSize``
* ``bitOffset``
* optional ``base``/type model and packing parameters

These define where the register exists in the hardware address space, and what type of value it is e.g. unsigned integer, floating point, etc.

Read/write calls trigger block transactions through the device/root transaction
pipeline.

Example
=======
The following example defines a control register with a single 8-bit unsigned integer field at address offset 0x00.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='Control',
               description='Control register field',
               offset=0x00,
               bitSize=8,
               bitOffset=0,
               mode='RW',
               base=pr.UInt,
           ))

RemoteVariable Class Documentation
==================================

.. autoclass:: pyrogue.RemoteVariable
   :members:
   :member-order: bysource
   :inherited-members:
