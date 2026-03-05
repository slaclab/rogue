# Rogue Docs Revamp Handoff

Last updated: 2026-03-04 (local workspace time)

## 1) Canonical Plan and Artifacts
Use these first; they are the authoritative plan artifacts created during this effort:

- `docs/src/documentation_plan/index.rst`
- `docs/src/documentation_plan/policies.rst`
- `docs/src/documentation_plan/page_templates.rst`
- `docs/src/documentation_plan/migration_matrix.rst`
- `docs/src/documentation_plan/m2_closeout.rst`

## 2) Milestone Status

- M1 Skeleton IA: complete
- M2 Narrative migration + boundary cleanup: complete (frozen and closeout recorded)
- M3 Coverage expansion: in progress (active)
- M4 Harmonization: not started

## 3) Key Decisions to Preserve

- Primary structure remains: Intro/Quick Start/Tutorials/Core docs/Reference split.
- API pages should be reference-first; narrative belongs in main docs.
- Sidebar can evolve at milestone boundaries (freeze inside milestone).
- `Installing`, `Logging`, and `PyDM` are currently top-level in sidebar.
- `API Reference` remains top-level.
- `Operations` is still present for now (temporary; may be revisited later).
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

- `docs/src/protocols/rssi/index.rst`
- `docs/src/protocols/rssi/client.rst`
- `docs/src/protocols/rssi/server.rst`

## 6) What Is Done vs Remaining

### Mostly done

- M2 IA moves and narrative/reference boundary structure.
- PyRogue Core / Stream / Memory narrative section scaffolding.
- Cookbook section created and seeded.
- Protocol sections for RSSI/SRP/Xilinx/Batcher/EPICSv4 substantially expanded.
- Protocol sections for UDP/Packetizer/UART expanded with code-backed content.
- C++ API protocol wrappers for UDP and Packetizer converted from placeholders
  to reference-oriented pages.

### Remaining high-value M3 work

1. Continue API<->narrative cross-link hardening (both directions).

2. M4-prep item already flagged in migration matrix:
   - `interfaces/index` broad conceptual narrative harmonization and final placement decisions.

3. Run docs build with warnings enabled in a Sphinx-enabled environment and
   resolve warnings introduced during protocol/API cleanup passes.

## 7) Suggested Next Execution Order (One Section at a Time)

1. API<->narrative cross-link hardening for protocol sections (bidirectional).
2. `interfaces/index` conceptual harmonization decisions (M4-prep).
3. Re-run docs build, then update migration matrix and add M3 closeout notes incrementally.

## 8) Fast Validation Checklist

- Build docs with warnings enabled after each section batch.
- Verify no `TODO` placeholder text remains in pages marked as covered.
- Verify lifecycle phrasing consistency for protocol pages that implement it.
- Verify no narrative regressions (content removed without relocation note).
- Verify internal links and toctree inclusion after moves.

## 9) Helpful Existing Pages to Reuse While Writing New Narrative

- `docs/src/protocols/network.rst`
- `docs/src/protocols/rssi/index.rst`
- `docs/src/protocols/srp/index.rst`
- `docs/src/protocols/batcher/index.rst`
- `docs/src/protocols/epicsV4/index.rst`
- `docs/src/pyrogue_core/client_access.rst`
- `docs/src/stream_interface/overview.rst`
