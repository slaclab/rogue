.. _tutorials_device_workflow_tutorial:

========================
Device Workflow Tutorial
========================

Goal
====

Build a maintainable custom device with clear variable, command, and model
structure suitable for production use.

Workflow
========

1. Start from the custom device example:
   :doc:`/getting_started/pyrogue_tree_example/p_t_device`
2. Refactor variable layout using:
   :doc:`/pyrogue_tree/core/variable`
3. Add command behavior patterns from:
   :doc:`/pyrogue_tree/core/command`
4. Apply model choices and type mapping guidance from:
   :doc:`/pyrogue_tree/core/model`
5. Validate full behavior with:
   :doc:`/getting_started/pyrogue_tree_example/full_root`

What This Tutorial Emphasizes
=============================

- Choosing between ``RemoteVariable``, ``LocalVariable``, and ``LinkVariable``
- Keeping command semantics explicit and testable
- Organizing blocks and models for long-term maintainability

API Reference
=============

- Python:
  :doc:`/api/python/pyrogue/device`
  :doc:`/api/python/pyrogue/basevariable`
  :doc:`/api/python/pyrogue/basecommand`
  :doc:`/api/python/pyrogue/model`