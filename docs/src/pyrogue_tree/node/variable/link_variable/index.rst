.. _pyrogue_tree_node_variable_link_variable:

============
LinkVariable
============

:py:class:`pyrogue.LinkVariable` exposes a derived value backed by one or more
dependency variables. It is useful for unit conversion, bit-field composition,
and user-friendly computed views.

Behavior
========

``LinkVariable`` typically uses:

* ``dependencies``: source variables used by linked logic
* ``linkedGet``: compute displayed value from dependencies
* ``linkedSet``: convert user value back to dependency writes

Example
=======

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='TempRaw',
               offset=0x100,
               bitSize=12,
               mode='RW',
               base=pr.UInt,
           ))
           

           self.add(pr.LinkVariable(
               name='Temperature',
               units='degC',
               mode='RW',
               dependencies=[self.TempRaw], # add()ed Nodes can be accessed as attributes
               linkedGet=lambda var, read=True: (var.dependencies[0].get(read=read) * 0.1) - 40.0,
               linkedSet=lambda var, value, write=True: var.dependencies[0].set(int((value + 40.0) / 0.1), write=write),
           ))

LinkVariable Class Documentation
================================

.. autoclass:: pyrogue.LinkVariable
   :members:
   :member-order: bysource
   :inherited-members:
