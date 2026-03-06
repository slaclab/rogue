.. _root_index:
.. _introduction:

=================================
Welcome to Rogue's documentation!
=================================

Rogue is a mixed C++/Python framework for building hardware control and data
acquisition applications. It provides reusable interfaces for moving streaming
data, accessing register maps, organizing systems into a hierarchical device
tree, and exposing that tree to tools such as GUIs, scripting, and higher-level
DAQ software.

In practice, Rogue is most useful when you need to combine:

* High-throughput data paths that run in C++ threads
* Structured hardware control and orchestration in Python
* A clean abstraction boundary between hardware transports and application logic

Whether you are bringing up a single board or coordinating a distributed
multi-server system, Rogue is designed to let you start quickly and scale
without rewriting core architecture.


Goals of Rogue
==============

The primary goal of Rogue is to accelerate data acquisition (DAQ) system
development while keeping performance and integration requirements manageable.

* Speed up system bring-up with reusable interfaces and building blocks.
* Support heterogeneous hardware and software connections through consistent
  transport and control abstractions.
* Provide easy-to-use abstractions for common access patterns such as register
  access, streaming data flow, and device orchestration.
* Preserve fine-grained operational control when detailed behavior tuning is
  required.
* Keep control logic decoupled from transport details so systems remain
  maintainable as requirements evolve.
* Scale from single-board setups to multi-node, multi-server deployments.
* Integrate with higher-level control ecosystems, including:

  * EPICS, CODA, Ignition (MySQL), EuDaq

Structure of Rogue
==================


Rogue uses a layered architecture that combines low-level performance with
high-level application development.

Mixed C++/Python Codebase
-------------------------

Rogue combines Python ergonomics with C++ performance. User-facing APIs are
exposed in Python, and most applications can be developed entirely in Python.
For performance-critical paths, equivalent C++ APIs are available when native
execution is required.

* C++ base classes expose core methods into Python.
* C++ threads handle bulk transport and communication mechanisms.
* Python enables rapid iteration, orchestration, and system composition.
* Performance-critical components can be implemented or migrated to C++.

High-Level Python Interfaces
----------------------------

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
------------------------

Below the Python layer, core interfaces provide deterministic access to data
movement and register transactions.

* :ref:`Stream Interface <interfaces_stream>` for bulk data movement and
  asynchronous messaging.
* :ref:`Memory Interface <interfaces_memory>` for register and memory-mapped
  access.

Additional Modules and Ecosystem Components
-------------------------------------------

Rogue also includes ecosystem modules that round out integration, operations,
and user-facing workflows.

* :ref:`Utilities <utilities>` for file I/O, PRBS tools, compression, and
  other support functions used during development and operations.
* :ref:`Protocols <protocols>` for transport and control integrations such
  as UDP, RSSI, SRP, packetizer, EPICS, and related protocol layers.
* :ref:`Hardware <hardware>` for hardware-facing drivers and interfaces,
  including AXI and raw memory-mapped access paths.
* :ref:`PyDM GUI support <pydm>` for Rogue channel integration and custom
  widgets used to monitor and control device trees.

To continue, proceed to :doc:`/quick_start/index`, or explore the sections in
the sidebar.


.. toctree::
   :hidden:
   :maxdepth: 3
   :caption: Contents:

   self
   /quick_start/index
   /tutorials/index
   /cookbook/index
   /installing/index
   /pyrogue_tree/index
   /stream_interface/index
   /memory_interface/index
   /built_in_modules/index
   /logging/index
   /pydm/index
   /migration/index
   /api/index
