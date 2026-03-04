.. _documentation_plan_migration_matrix:

================
Migration Matrix
================

This matrix tracks where content is moving as the revamp proceeds.

+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| Old Path                                          | New Path                                   | Action | Owner     | Milestone   |
+===================================================+============================================+========+===========+=============+
| /getting_started/index                            | /quick_start/index                         | Link   | Docs Team | M1 Skeleton |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /getting_started/pyrogue_tree_example/*           | /tutorials/index                           | Link   | Docs Team | M1 Skeleton |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /pyrogue_tree/index                               | /pyrogue_core/index                        | Link   | Docs Team | M1 Skeleton |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/stream/index                          | /stream_interface/index                    | Link   | Docs Team | M1 Skeleton |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/memory/index                          | /memory_interface/index                    | Link   | Docs Team | M1 Skeleton |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /utilities/*, /hardware/*, /protocols/*            | /built_in_modules/index                  | Link   | Docs Team | M2 IA       |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/clients/*, /interfaces/pyrogue/*      | /pyrogue_core/index                        | Move   | Docs Team | M2 IA       |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/stream/*                              | /stream_interface/index                    | Move   | Docs Team | M2 IA       |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/memory/*                              | /memory_interface/index                    | Move   | Docs Team | M2 IA       |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/stream/index narrative                | /stream_interface/overview                 | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/memory/index narrative                | /memory_interface/overview                 | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/clients/index narrative               | /pyrogue_core/client_access                | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/pyrogue/index narrative               | /pyrogue_core/client_access                | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/simulation/index narrative            | /built_in_modules/integrations             | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/version narrative                     | /built_in_modules/integrations             | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/sql narrative                         | /built_in_modules/integrations             | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /api/cpp/interfaces/memory/transaction            | /memory_interface/transactions             | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /advanced_examples/index                          | /cookbook/index                            | Link   | Docs Team | M3 Coverage |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /custom_module/index                              | /stream_interface/index                    | Move   | Docs Team | M3 Coverage |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /logging/*, /pydm/*, /installing/*                | /operations/index                          | Link   | Docs Team | M1 Skeleton |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+

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
