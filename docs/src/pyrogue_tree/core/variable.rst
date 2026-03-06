.. _pyrogue_tree_node_variable:

========
Variable
========

Variables are the value-carrying Nodes in the PyRogue tree. They provide:

* a typed value Model (display/native formatting, units, enum support)
* access mode control (``RW``, ``RO``, ``WO``)
* optional hardware I/O through Block transactions
* listener/update integration for GUIs and remote interfaces

Variable Types
==============

PyRogue provides three primary Variable subtypes:

.. toctree::
   :maxdepth: 1
   :caption: Types of Variables in the PyRogue Tree:

   link_variable
   local_variable
   remote_variable

When to use each type
=====================

* :py:class:`pyrogue.LocalVariable`: value is computed/stored locally in Python.
* :py:class:`pyrogue.RemoteVariable`: value maps to hardware memory/register space.
* :py:class:`pyrogue.LinkVariable`: value is derived from one or more dependency
  Variables via custom getter/setter logic.

Variable stream adapters
========================

Use Variable stream adapters when value updates should feed downstream stream
processing or external consumers, instead of relying only on direct tree
queries.

Common patterns:

* push Variable changes into stream pipelines for asynchronous processing
* bridge selected telemetry into stream-capable transport/recording paths
* isolate conversion/formatting at the adapter boundary

For the stream-variable interface layer, see
:doc:`/pyrogue_core/python_interfaces/memory_stream_variable`.

Common attributes and behavior
==============================

Most Variable classes share:

* ``mode``: one of ``RW``, ``RO``, ``WO``
* ``value`` / ``disp`` / ``enum`` / ``units``
* ``minimum`` / ``maximum`` constraints
* group tags and filtering behavior
* update notifications/listeners

Polling note: Variables with non-zero ``pollInterval`` participate in the root
poll scheduler. See :ref:`pyrogue_tree_root_poll_queue` for scheduling details
and usage patterns.

Implementation Boundary (Python and C++)
========================================

For :py:class:`pyrogue.RemoteVariable`, the public Python object wraps a
lower-level memory Variable implementation from ``rogue.interfaces.memory``.

This means:

* Python-facing configuration (mode, formatting, limits, groups) is handled in
  PyRogue classes
* byte/bit packing, access-range tracking, and typed conversion paths are
  executed in the memory interface runtime (primarily C++ Block/Variable logic)
* transactions are still orchestrated through Block and Device APIs

See also:

* :ref:`pyrogue_tree_node_block`
* :doc:`/pyrogue_tree/core/block`
* :doc:`/memory_interface/index`

BaseVariable API Reference
================================

See :doc:`/api/python/basevariable` for generated API details.
