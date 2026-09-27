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


.. toctree::
   :hidden:
   :maxdepth: 3
   :caption: Overview:

   Introduction <self>
   /overview/structure

.. toctree::
   :hidden:
   :maxdepth: 3
   :caption: Getting Started:

   /installing/index
   /tutorials/index
   /cookbook/index

.. toctree::
   :hidden:
   :maxdepth: 3
   :caption: Reference:

   /pyrogue_tree/index
   /stream_interface/index
   /memory_interface/index
   /built_in_modules/index
   /logging/index
   /pydm/index
   /api/index
   /migration/index
