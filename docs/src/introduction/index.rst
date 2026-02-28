.. _introduction:

============
Introduction
============

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

Rogue is designed to facilitate hardware development and intermediate DAQ
systems by providing a consistent, extensible software foundation.

* Support multiple hardware and software interface technologies, including
  future transports and protocols.
* Provide clear mechanisms for connecting independent management and data
  processing modules through well-defined interfaces.
* Run high-performance data paths in independent C++ threads while still
  enabling Python-side access for inspection and visualization.
* Offer a flexible hierarchy for composing system components independent of
  physical network or hardware boundaries.
* Coordinate and manage multi-node or multi-server deployments.
* Support data writing, replay, and configuration archiving for debug and
  operations workflows.
* Interface with higher-level control and management layers, including:

  * EPICS
  * CODA
  * Ignition (MySQL)
  * EuDaq



Structure of Rogue
==================


Rogue uses a layered architecture that combines low-level performance with
high-level application development.

* Mixed C++/Python codebase (via Boost.Python bindings):

  * C++ base classes expose core methods into Python.
  * C++ threads handle bulk transport and communication mechanisms.
  * Python enables rapid iteration, orchestration, and system composition.
  * Performance-critical components can be implemented or migrated to C++.

* High-level Python interfaces:

  * :ref:`Tree-based <pyrogue_tree>` structure for hierarchical system
    organization.
  * Devices can contain Variables, Commands, and other Devices.
  * These objects derive from the :ref:`Node <pyrogue_tree_node>` base class.
  * :ref:`Variables <pyrogue_tree_node_variable>` describe register data
    (addressing, type, access behavior, and display semantics).
  * :ref:`Commands <pyrogue_tree_node_command>` define operational procedures
    and control actions.

* Low-level C++ interfaces:

  * :ref:`Stream Interface <interfaces_stream>` for bulk data movement and
    asynchronous messaging (`rogue::interfaces::stream`).
  * :ref:`Memory Interface <interfaces_memory>` for register and memory-mapped
    access (`rogue::interfaces::memory`).

* Additional modules and ecosystem components:

  * :ref:`Utilities <utilities>` for file I/O, PRBS tools, compression, and
    other support functions used during development and operations.
  * :ref:`Protocols <protocols>` for transport and control integrations such
    as UDP, RSSI, SRP, packetizer, EPICS, and related protocol layers.
  * :ref:`Hardware <hardware>` for hardware-facing drivers and interfaces,
    including AXI and raw memory-mapped access paths.
  * :ref:`PyDM GUI support <pydm>` for Rogue channel integration and custom
    widgets used to monitor and control device trees.

To continue, see :ref:`interfaces` for transport-level APIs and
:ref:`starting_tutorials` for a hands-on starting path.
