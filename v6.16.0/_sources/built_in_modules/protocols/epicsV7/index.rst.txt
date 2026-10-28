.. _protocols_epicsv7:

================
EPICS V7 Access
================

EPICS-facing protocol integration using softIocPVA (pythonSoftIOC) to serve
PyRogue Variables as real EPICS records. The V7 integration supports both CA
and PVA client access.

Use these pages for conceptual behavior and integration patterns. Generated
API pages are available in the Python API reference:

- :doc:`/api/python/pyrogue/protocols/epicsv7/index`

How The EPICS V7 Integration Is Structured
==========================================

The EPICS V7 integration has two primary components:

- ``EpicsPvServer`` scans the running PyRogue tree, selects Variables to
  expose, and creates the EPICS record namespace using softIocPVA.
- ``EpicsPvHolder`` represents one served record and handles value updates,
  type mapping, and EPICS put behavior for its bound Variable or Command.

In practice, ``EpicsPvServer`` owns many ``EpicsPvHolder`` instances.

Key Differences from EPICS V4
==============================

The V7 integration uses softioc (pythonSoftIOC) instead of p4p. This provides:

- **Real EPICS records** — softIocPVA creates longIn/longOut, ai/ao, and
  other record types rather than SharedPV objects.
- **Commands via caput** — PyRogue Commands are exposed as longOut records.
  Clients invoke them with a plain put (value is forwarded as the command
  argument), not with an RPC call.

.. note::

   Neither softioc nor p4p exposes a Python callback that fires when a CA or
   PVA client issues a ``caget`` / ``ctxt.get()``. Both EPICS V4 and V7
   integrations serve the most recently pushed value from the EPICS record
   buffer. To ensure clients receive up-to-date hardware values, the Rogue
   server process must execute hardware reads itself — either via PyRogue
   auto-polling (``pollInterval`` on variables or ``pollEn=True`` on the
   Root) or by calling device-level read commands explicitly.

Installation
============

Install the softioc dependency with::

    pip install softioc

or add ``softioc`` to your conda environment.

Typical Workflow
================

1. Start a PyRogue ``Root`` and ensure Variables are tagged with the intended
   include and exclude groups.
2. Create
   ``EpicsPvServer(base=..., root=..., incGroups=..., excGroups=..., pvMap=...)``.
3. Register it with the ``Root`` protocol lifecycle and inspect the resulting
   mapping with ``list()`` or ``dump()``.
4. Validate end-to-end behavior with any EPICS client (CA or PVA).

Group Filtering
===============

Variable exposure is controlled by normal PyRogue group filtering.
``incGroups`` includes only matching Variables when it is set, and
``excGroups`` excludes matching Variables. The default exclusion list includes
``NoServe``.

For group semantics and filtering behavior in the tree model, see
:doc:`/pyrogue_tree/core/groups`.

Subtopics
=========

- Server setup and PV mapping details: :doc:`epicspvserver`
- Per-variable publication behavior: :doc:`epicspvholder`

Related Topics
==============

- EPICS V4 integration (p4p-based): :doc:`/built_in_modules/protocols/epicsV4/index`
- General protocol overview: :doc:`/built_in_modules/protocols/index`
- Tree group filtering: :doc:`/pyrogue_tree/core/groups`

.. toctree::
   :maxdepth: 1
   :caption: EPICS V7 Access

   epicspvserver
   epicspvholder
