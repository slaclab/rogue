.. _documentation_plan_migration_matrix:

================
Migration Matrix
================

This matrix tracks where content is moving as the revamp proceeds.

.. list-table:: Migration Matrix
   :header-rows: 1
   :widths: 34 28 10 10 14

   * - Old Path
     - New Path
     - Action
     - Owner
     - Milestone
   * - /getting_started/index
     - /quick_start/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /getting_started/pyrogue_tree_example/*
     - /tutorials/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /pyrogue_tree/index
     - /pyrogue_core/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /interfaces/stream/index
     - /stream_interface/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /interfaces/memory/index
     - /memory_interface/index
     - Link
     - Docs Team
     - M1 Skeleton
   * - /utilities/*, /hardware/*, /protocols/*
     - /built_in_modules/index
     - Link
     - Docs Team
     - M2 IA [done]
   * - /interfaces/clients/*, /interfaces/pyrogue/*
     - /pyrogue_core/index
     - Move
     - Docs Team
     - M2 IA [done]
   * - /interfaces/stream/*
     - /stream_interface/index
     - Move
     - Docs Team
     - M2 IA [done]
   * - /interfaces/memory/*
     - /memory_interface/index
     - Move
     - Docs Team
     - M2 IA [done]
   * - /interfaces/stream/index narrative
     - /stream_interface/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/memory/index narrative
     - /memory_interface/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/clients/index narrative
     - /pyrogue_core/client_access
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/pyrogue/index narrative
     - /pyrogue_core/client_access
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/simulation/index narrative
     - /built_in_modules/integrations
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/version narrative
     - /built_in_modules/integrations
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/sql narrative
     - /built_in_modules/integrations
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /utilities/index narrative
     - /built_in_modules/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /hardware/index narrative
     - /built_in_modules/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/index narrative
     - /built_in_modules/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /installing/index narrative
     - /operations/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /logging/index narrative
     - /operations/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /pydm/index narrative
     - /operations/overview
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/simulation/mememulate placeholder
     - /built_in_modules/integrations
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/simulation/pgp2b placeholder
     - /built_in_modules/integrations
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/simulation/sideband placeholder
     - /built_in_modules/integrations
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/udp/index placeholder
     - /protocols/udp/index
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/udp/client placeholder
     - /protocols/udp/client
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/udp/server placeholder
     - /protocols/udp/server
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/packetizer/index placeholder
     - /protocols/packetizer/index
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/packetizer/core placeholder
     - /protocols/packetizer/core
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/packetizer/coreV2 placeholder
     - /protocols/packetizer/coreV2
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/epicsV4/index placeholder
     - /protocols/epicsV4/index
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /protocols/uart placeholder
     - /protocols/uart
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /api/cpp/protocols/udp/* placeholder
     - /api/cpp/protocols/udp/*
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /api/cpp/protocols/packetizer/* placeholder
     - /api/cpp/protocols/packetizer/*
     - Link
     - Docs Team
     - M2 Narrative [done]
   * - /migration/rogue_v6 TBD links
     - /migration/rogue_v6
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /interfaces/memory/hub TBD links
     - /interfaces/memory/hub
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /api/cpp/interfaces/memory/transaction
     - /memory_interface/transactions
     - Move
     - Docs Team
     - M2 Narrative [done]
   * - /advanced_examples/index
     - /cookbook/index
     - Link
     - Docs Team
     - M3 Coverage
   * - /custom_module/index
     - /stream_interface/index
     - Move
     - Docs Team
     - M3 Coverage
   * - /logging/*, /pydm/*, /installing/*
     - /operations/index
     - Link
     - Docs Team
     - M1 Skeleton

Status keys:

- Link: new section points to existing content.
- Move: narrative content moved to new canonical page.
- Split: existing page split into conceptual/how-to/reference pages.

Execution guardrail for current phase:

- Preserve existing narrative text; move/relink it rather than deleting it.

Deferred API Reorg Notes
========================

- Reorganize the Python API section so ``Model`` and model subclasses have a
  dedicated grouped entry/page set (tracked for later milestone work).

Deferred Content Expansion Notes
================================

- Expand Quick Start and Tutorials with distinct, non-overlapping content:
  Quick Start for first success path, Tutorials for deeper workflows.
- Expand Protocol pages that currently have minimal narrative into full concept
  and example coverage.
