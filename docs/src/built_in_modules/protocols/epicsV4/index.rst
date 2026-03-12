.. _protocols_epicsv4:
.. _protocols_epics:

================
EPICSV4 Protocol
================

EPICS-facing protocol integration in Rogue/PyRogue is built around serving
selected PyRogue Variables into an EPICS V4 namespace.

Use these pages for conceptual behavior and integration patterns. API object
details remain in the Python API reference.

How the EPICS integration is structured
=======================================

The EPICS V4 integration has two primary components:

- ``EpicsPvServer``:
  scans the running PyRogue tree, selects variables to expose, and creates the
  EPICS PV namespace.
- ``EpicsPvHolder``:
  represents one served PV, handling value updates, type mapping, and EPICS
  put/rpc behavior for its bound variable.

In practice, ``EpicsPvServer`` owns many ``EpicsPvHolder`` instances.

Recommended reading order
=========================

1. Start with :doc:`epicspvserver` to understand server setup and PV mapping.
2. Then read :doc:`epicspvholder` for per-variable behavior details.

Typical workflow
================

1. Start a PyRogue root and ensure variables are in the intended include/exclude groups.
2. Create ``EpicsPvServer(base=..., root=..., incGroups=..., excGroups=..., pvMap=...)``.
3. Register it with the root protocol lifecycle and validate mappings with
   ``list()`` / ``dump()``.
4. Validate end-to-end behavior with an EPICS client (see ``tests/test_epics.py``).

Group filtering model
=====================

Variable exposure is controlled by normal PyRogue group filtering:

- ``incGroups`` includes only matching variables when set.
- ``excGroups`` excludes matching variables (default includes ``NoServe``).

This lets you keep one tree model while exposing only the intended EPICS PV
surface for a given deployment.

For group semantics and filtering behavior in the tree model, see
:doc:`/pyrogue_tree/core/groups`.

Related Topics
==============

- :doc:`/api/python/pyrogue/protocols/epicsv4/epicspvserver`
- :doc:`/api/python/pyrogue/protocols/epicsv4/epicspvholder`
- :doc:`/built_in_modules/protocols/index`

.. toctree::
   :maxdepth: 1
   :caption: EPICSV4 Protocol

   epicspvserver
   epicspvholder
