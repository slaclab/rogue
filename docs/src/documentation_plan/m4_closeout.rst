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

Completion summary
==================

M4 harmonization is complete as of 2026-03-11.

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

- Documentation builds were run incrementally after section batches.
- Final HTML build completed successfully in the project ``rogue_build``
  environment.
- Remaining reported warning was environmental: intersphinx could not fetch the
  Python inventory because external network access was unavailable.

Release freeze checks
=====================

- Major section landing pages include substantive narrative content.
- API pages remain reference-first with concise conceptual links.
- Milestone artifacts were aligned for merge.
- Legacy example sections remain available as supplemental material rather than
  canonical navigation roots.

Finalization notes
==================

- M4 status was marked complete in handoff and plan artifacts.
- Structural moves are now frozen for this revamp branch.
- Any further expansion should be handled as post-merge follow-up work.
