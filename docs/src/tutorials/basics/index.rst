.. _basics:

==========
Basics
==========

This should be a paragraph/abstract that defines what rogue is at a quick glance.
This section goes into depth about what rogue is, and situations in which you might use it.
This is where I should put starter information and include various notes from the powerpoint slide.


Goals of Rogue
==============

Provide a system to facilitate hardware development and intermediate daq systems
for interfacing to hardware

* Support a number of hardware & software interface technologies, including ones that don’t yet exist
* Easy to understand mechanisms for connecting independent management and data processing modules together using a set of well defined, easy to understand interfaces
* Allow data paths to exist in independent high performance threads
   
   * While also allowing data access to python for visualization

* Flexible structure for creating a hierarchy of system components
   
   * Independent of the network and hardware hierarchies

* Internode coordination and management of multi-server systems (RCE clusters)
* Support data file writing & configuration archiving
* Interface independently to a number of management layers, sometimes in parallel
   
   * EPICS
   * CODA
   * Ignition (mysql)
   * EuDaq



Structure of Rogue
==================


* Mixed C++/Python codebase using boost::python library

   * C++ base classes expose most of their methods to Python layer
   * C++ threads are used for data path and underlying communication mechanisms
   * Allows rapid development in Python with ability to drop into C++ for performance
   * Most development with Rogue is done in Python

* Low level (C++) base structures

   * Stream interface for bulk data movement and asynchronous messages

      * Rogue::interfaces::stream

   * Memory interface for register access

      * Rogue::interfaces::memory

* Higher level (Python) :ref:`interfaces` for organizing systems

   * :ref:`pyrogue_tree` structure for hierarchical organization.
   * Devices contain Variables, Commands, and other Devices

      * These are all a part of the :ref:`pyrogue_tree_node`(Node) base class

   * Variables describe registers - Address, data type, etc: :ref:`pyrogue_tree_node_variable`
   * Commands describe common sequences of operations on a Device :ref:`pyrogue_tree_node_command`

