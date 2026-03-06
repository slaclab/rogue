.. _documentation_plan_m4_closeout:

===========
M4 Closeout
===========

M4 objective
============

Complete harmonization of the documentation structure after major migration:

- remove stale/transitional navigation patterns
- normalize naming, ordering, and section conventions
- converge moved content into canonical narrative homes
- finalize cross-link boundaries between narrative and API reference pages

Completion summary (Draft)
==========================

M4 harmonization is in closeout preparation.

Completed in M4 so far:

- Canonical top-level navigation was stabilized with ``Installing``,
  ``Logging``, and ``PyDM`` as top-level sections.
- Legacy ``interfaces`` content was re-homed into canonical sections and then
  integrated into narrative-first destinations.
- ``stream_interface`` and ``memory_interface`` legacy subfolders were fully
  integrated and removed.
- ``built_in_modules`` routing pages were collapsed; simulation/sql/version/cpp
  topics were normalized into canonical pages.
- ``pyrogue_core`` transitional narrative content was moved into canonical
  ``pyrogue_tree``/``cookbook``/``built_in_modules`` homes and removed.
- ``pyrogue_tree`` structure was normalized around ``core``,
  ``builtin_devices``, and ``client_interfaces`` with consistent toctrees.
- ``OS Memory Bridge`` docs were consolidated into one canonical narrative page.
- Variable stream adapter narrative was re-homed under
  ``pyrogue_tree/core/memory_variable_stream``.
- API interface pages were normalized to point at canonical conceptual docs.
- Section-level consistency passes were completed for:
  ``pyrogue_tree/client_interfaces``, ``built_in_modules/simulation``, and core
  built-in module pages.

Validation
==========

- Documentation builds are being run incrementally after section batches.
- Current reported state from latest user validation: no build warnings.

Release freeze checks
=====================

- Confirm no remaining stale destination paths in planning artifacts.
- Confirm all major section landing pages include substantive narrative content.
- Confirm API pages remain reference-first with concise conceptual links.
- Confirm milestone artifacts (handoff + matrix + closeout docs) align.

Finalization notes
==================

When release freeze is declared:

- mark M4 status as complete in handoff and plan artifacts
- add final date stamp in this document
- lock further structural moves to post-release follow-up work
