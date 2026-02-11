.. _pyrogue_tree_node_variable:

========
Variable
========

Variables are the value-carrying nodes in the PyRogue tree. They provide:

* a typed value model (display/native formatting, units, enum support)
* access mode control (``RW``, ``RO``, ``WO``)
* optional hardware I/O through block transactions
* listener/update integration for GUIs and remote interfaces

Variable Types
==============

PyRogue provides three primary variable subtypes:

.. toctree::
   :maxdepth: 1
   :caption: Types of Variables in the PyRogue Tree:

   link_variable/index
   local_variable/index
   remote_variable/index

When to use each type
=====================

* :py:class:`pyrogue.LocalVariable`: value is computed/stored locally in Python.
* :py:class:`pyrogue.RemoteVariable`: value maps to hardware memory/register space.
* :py:class:`pyrogue.LinkVariable`: value is derived from one or more dependency
  variables via custom getter/setter logic.

Common attributes and behavior
==============================

Most variable classes share:

* ``mode``: one of ``RW``, ``RO``, ``WO``
* ``value`` / ``disp`` / ``enum`` / ``units``
* ``minimum`` / ``maximum`` constraints
* group tags and filtering behavior
* update notifications/listeners

BaseVariable Class Documentation
================================

.. autoclass:: pyrogue.BaseVariable
   :members:
   :member-order: bysource
   :inherited-members:
