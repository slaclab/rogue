# Rogue Docs Revamp Handoff

Last updated: 2026-03-06 (local workspace time)

## 1) Canonical Plan and Artifacts
Use these first; they are the authoritative plan artifacts created during this effort:

- `docs/src/documentation_plan/index.rst`
- `docs/src/documentation_plan/policies.rst`
- `docs/src/documentation_plan/page_templates.rst`
- `docs/src/documentation_plan/migration_matrix.rst`
- `docs/src/documentation_plan/m2_closeout.rst`
- `docs/src/documentation_plan/m3_closeout.rst`
- `docs/src/documentation_plan/m4_closeout.rst`

## 2) Milestone Status

- M1 Skeleton IA: complete
- M2 Narrative migration + boundary cleanup: complete (frozen and closeout recorded)
- M3 Coverage expansion: complete (closeout recorded)
- M4 Harmonization: closeout preparation active

## 3) Key Decisions to Preserve

- Primary structure remains: Intro/Quick Start/Tutorials/Core docs/Reference split.
- API pages should be reference-first; narrative belongs in main docs.
- Sidebar can evolve at milestone boundaries (freeze inside milestone).
- `API Reference` remains top-level.
- `Installing`, `Logging`, and `PyDM` are top-level documentation sections.
- `utilities + hardware + protocols` were grouped under `built_in_modules` as part of IA.
- No accidental narrative deletion policy was enforced in M2.
- M3 policy update from user: revising/expanding narrative is now allowed; call out meaningful revisions; if narrative no longer fits, mark and report it.
- “Operational checklist” sections were deemed low-value; replace with code-backed narrative from implementation + examples/tests.

## 4) Protocol-Specific Decisions Already Made

- `protocols/epics` content was merged into `protocols/epicsV4`; links were updated accordingly.
- Batcher docs were consolidated:
  - `inverterV1 + inverterV2 -> protocols/batcher/inverter.rst`
  - `splitterV1 + splitterV2 -> protocols/batcher/splitter.rst`
- Lifecycle terminology standardized:
  - Name: **Managed Interface Lifecycle**
  - Reference target: `:ref:\`pyrogue_tree_node_device_managed_interfaces\``
- Start/stop yes/no markers were removed.
- Current preferred protocol section style:
  - Single `Threading and Lifecycle` section where applicable.
  - If class implements lifecycle, use one bullet:
    - `Implements Managed Interface Lifecycle:`
      `:ref:\`pyrogue_tree_node_device_managed_interfaces\``
  - If relevant, add a thread behavior bullet (background thread / controller-owned execution).

## 5) Current Workspace State (Important)

There are uncommitted local changes in protocol pages related to lifecycle/threading cleanup. New agent should inspect before additional refactors:

- `docs/src/built_in_modules/protocols/rssi/index.rst`
- `docs/src/built_in_modules/protocols/rssi/client.rst`
- `docs/src/built_in_modules/protocols/rssi/server.rst`

## 6) What Is Done vs Remaining

### Mostly done

- M2 IA moves and narrative/reference boundary structure.
- PyRogue Core / Stream / Memory narrative section scaffolding.
- Cookbook section created and seeded.
- Protocol sections for RSSI/SRP/Xilinx/Batcher/EPICSv4 substantially expanded.
- Protocol sections for UDP/Packetizer/UART expanded with code-backed content.
- C++ API protocol wrappers for UDP and Packetizer converted from placeholders
  to reference-oriented pages.
- `interfaces/index` conceptual harmonization completed as a transitional map to
  canonical section homes.
- M4 started: canonical section toctrees cleaned to remove stale legacy-path
  entries while preserving explicit links to legacy integration pages.
- M4 continued: landing-page terminology/order harmonization was applied across
  introduction/documentation index/core section landing pages.
- M4 nav decision update: restored `Installing`/`Logging`/`PyDM` as top-level
  entries.
- M4 continued: legacy ``interfaces`` index pages for client/pyrogue/stream/
  memory were re-homed into canonical section toctrees (PyRogue Core, Stream
  Interface, Memory Interface).
- M4 continued: files under ``interfaces/clients`` and ``interfaces/pyrogue``
  were physically moved into ``pyrogue_core/client_interfaces`` and
  ``pyrogue_core/python_interfaces``, and links were updated.
- M4 continued: files under ``interfaces/stream`` and ``interfaces/memory``
  were physically moved into ``stream_interface/legacy_stream`` and
  ``memory_interface/legacy_memory``, and links were updated.
- M4 continued: ``stream_interface/legacy_stream`` was fully integrated into
  parent ``stream_interface`` narrative pages; links/toctrees were updated and
  ``legacy_stream`` was removed.
- M4 continued: ``memory_interface/legacy_memory`` was fully integrated into
  parent ``memory_interface`` narrative pages; links/toctrees were updated and
  ``legacy_memory`` was removed.
- M4 continued: ``built_in_modules`` routing pages were collapsed into a
  narrative-first ``built_in_modules/index``; ``overview``/``integrations``
  were removed, and simulation/sql pages were expanded from placeholders into
  code-backed guidance.
- M4 continued: remaining ``interfaces`` content was physically moved:
  ``interfaces/simulation/*`` -> ``built_in_modules/simulation/*``,
  ``interfaces/sql`` -> ``built_in_modules/sql``, ``interfaces/version`` ->
  ``built_in_modules/version``, and ``interfaces/cpp_api`` ->
  ``built_in_modules/cpp_api_wrapper``.

### Remaining high-value M4 work

Continue M4 harmonization and release-freeze cleanup.

## 7) Suggested Next Execution Order (One Section at a Time)

1. M4 harmonization sweep: normalize naming/ordering and remove stale navigation
   paths where safe.
2. Final consistency pass across section landing pages (terminology and
   cross-links).
3. Release-ready freeze/update of plan artifacts after M4 decisions land.

## 8) Fast Validation Checklist

- Build docs with warnings enabled after each section batch.
- Verify no `TODO` placeholder text remains in pages marked as covered.
- Verify lifecycle phrasing consistency for protocol pages that implement it.
- Verify no narrative regressions (content removed without relocation note).
- Verify internal links and toctree inclusion after moves.

## 9) Helpful Existing Pages to Reuse While Writing New Narrative

- `docs/src/built_in_modules/protocols/network.rst`
- `docs/src/built_in_modules/protocols/rssi/index.rst`
- `docs/src/built_in_modules/protocols/srp/index.rst`
- `docs/src/built_in_modules/protocols/batcher/index.rst`
- `docs/src/built_in_modules/protocols/epicsV4/index.rst`
- `docs/src/pyrogue_core/client_access.rst`
- `docs/src/stream_interface/index.rst`
