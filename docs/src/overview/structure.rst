.. _structure:

==================
Structure of Rogue
==================


Rogue uses a layered architecture that combines low-level performance with
high-level application development.

Mixed C++/Python Codebase
=========================

Rogue combines Python ergonomics with C++ performance. User-facing APIs are
exposed in Python, and most applications can be developed entirely in Python.
For performance-critical paths, equivalent C++ APIs are available when native
execution is required.

* C++ base classes expose core methods into Python.
* C++ threads handle bulk transport and communication mechanisms.
* Python enables rapid iteration, orchestration, and system composition.
* Performance-critical components can be implemented or migrated to C++.

High-Level Python Interfaces
============================

At the application layer, Rogue uses a tree model that keeps system structure
explicit and manageable.

* :ref:`Tree-based <pyrogue_tree>` structure for hierarchical system
  organization.
* Devices can contain Variables, Commands, and other Devices.
* These objects derive from the :ref:`Node <pyrogue_tree_node>` base class.
* :ref:`Variables <pyrogue_tree_node_variable>` describe register data
  (addressing, type, access behavior, and display semantics).
* :ref:`Commands <pyrogue_tree_node_command>` define operational procedures
  and control actions.

Low-Level C++ Interfaces
========================

Below the Python layer, core interfaces provide deterministic access to data
movement and register transactions.

* :ref:`Stream Interface <interfaces_stream>` for bulk data movement and
  asynchronous messaging.
* :ref:`Memory Interface <interfaces_memory>` for register and memory-mapped
  access.

Additional Modules and Ecosystem Components
===========================================

Rogue also includes ecosystem modules that round out integration, operations,
and user-facing workflows.

* :doc:`/built_in_modules/index` groups reusable integration modules,
  including:
  :ref:`Utilities <utilities>` for file I/O, PRBS tools, compression, and
  other support functions,
  :ref:`Protocols <protocols>` for transport/control integrations such as UDP,
  RSSI, SRP, and packetizer,
  and :ref:`Hardware <hardware>` interfaces for AXI and raw memory-mapped
  access paths.
* :ref:`PyDM GUI support <pydm>` for Rogue channel integration and custom
  widgets used to monitor and control device trees.