.. _protocols_xilinx_classes_xvc:

===
Xvc
===

Threading and Lifecycle
=======================

- ``Xvc`` runs a background server thread for TCP XVC clients.
- Implements Managed Interface Lifecycle:
  :ref:`pyrogue_tree_node_device_managed_interfaces`

For conceptual guidance, see :doc:`/protocols/xilinx/index`.

Xvc objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::xilinx::XvcPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::xilinx::Xvc
   :members:
