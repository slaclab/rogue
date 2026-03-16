.. _protocols_epicsv4:
.. _protocols_epics:

================
EPICS V4 Access
================

EPICS-facing protocol integration in Rogue and PyRogue is built around serving
selected PyRogue Variables into an EPICS V4 namespace.

Use these pages for conceptual behavior and integration patterns. API object
details remain in the Python API reference.

How The EPICS Integration Is Structured
=======================================

The EPICS V4 integration has two primary components:

- ``EpicsPvServer`` scans the running PyRogue tree, selects Variables to
  expose, and creates the EPICS PV namespace.
- ``EpicsPvHolder`` represents one served PV and handles value updates, type
  mapping, and EPICS put/rpc behavior for its bound Variable or Command.

In practice, ``EpicsPvServer`` owns many ``EpicsPvHolder`` instances.

Typical Workflow
================

1. Start a PyRogue ``Root`` and ensure Variables are tagged with the intended
   include and exclude groups.
2. Create
   ``EpicsPvServer(base=..., root=..., incGroups=..., excGroups=..., pvMap=...)``.
3. Register it with the ``Root`` protocol lifecycle and inspect the resulting
   mapping with ``list()`` or ``dump()``.
4. Validate end-to-end behavior with an EPICS client.

Group Filtering
===============

Variable exposure is controlled by normal PyRogue group filtering.
``incGroups`` includes only matching Variables when it is set, and
``excGroups`` excludes matching Variables. The default exclusion list includes
``NoServe``, which lets one tree support multiple deployments while exposing
only the intended EPICS PV surface.

For group semantics and filtering behavior in the tree model, see
:doc:`/pyrogue_tree/core/groups`.

Subtopics
=========

- Server setup and PV mapping details: :doc:`epicspvserver`
- Per-variable publication behavior: :doc:`epicspvholder`

Related Topics
==============

- General protocol overview: :doc:`/built_in_modules/protocols/index`
- Tree group filtering: :doc:`/pyrogue_tree/core/groups`

.. toctree::
   :maxdepth: 1
   :caption: EPICS V4 Access

   epicspvserver
   epicspvholder
