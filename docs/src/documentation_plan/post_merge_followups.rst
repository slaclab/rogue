.. _documentation_plan_post_merge_followups:

=========================
Post-Merge Follow-Up List
=========================

This page records work intentionally deferred from the documentation revamp so
it can be tackled in later PRs without reopening the release-freeze scope.

High-priority follow-up candidates
==================================

- Expand cookbook breadth with short recipes for:

  - polling workflows
  - YAML configuration/state/status workflows
  - built-in device usage patterns
  - stream transport integration patterns

- Expand stream/threading cookbook coverage with:

  - threaded receive worker patterns
  - queue backpressure and overload handling policies
  - shutdown-safe worker lifecycle patterns
  - C++ analogs for the current Python-focused examples

- Continue protocol/API cross-link hardening where conceptual narrative and API
  reference boundaries are still rough.

Navigation and IA cleanup
=========================

- Decide whether ``/getting_started/index`` should remain a visible supplemental
  tutorial entry or move fully behind links from canonical narrative pages.
- Decide whether ``/advanced_examples/index`` should remain in the tutorials and
  cookbook context or be retired to a lower-visibility legacy/examples area.
- Decide whether ``/custom_module/index`` should stay as a standalone section or
  be fully absorbed into ``/stream_interface`` and cookbook material.

Content depth improvements
==========================

- Add more end-to-end cookbook material for:

  - advanced ``Device`` composition
  - complex ``RemoteVariable`` mappings
  - ``LinkVariable`` dependency design and troubleshooting
  - stream diagnostics and validation workflows

- Review tutorial pages and replace link-heavy outlines with more fully worked
  walkthrough narrative where it adds clear user value.
- Review legacy example pages and decide which should be modernized versus
  preserved only as compatibility references.

Reference polish
================

- Continue refining generated Python/C++ API landing pages where grouping or
  ordering can better match how users look up classes.
- Revisit deep API navigation settings after users have had time to use the new
  structure in practice.

Environment and tooling follow-ups
==================================

- Consider configuring intersphinx or build settings so offline doc builds do
  not warn when external inventories are unreachable.
- Consider setting ``MPLCONFIGDIR`` in the docs build task environment to avoid
  matplotlib cache warnings in restricted environments.

Scope note
==========

- None of the items on this page blocked the revamp merge into ``pre-release``.
- Structural migration and M4 harmonization were considered complete before
  this backlog was recorded.
