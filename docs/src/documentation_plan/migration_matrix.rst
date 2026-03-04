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
| /utilities/index, /hardware/index, /protocols/index | /built_in_modules/index                  | Link   | Docs Team | M2 IA       |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/clients/*, /interfaces/pyrogue/*      | /pyrogue_core/index                        | Move   | Docs Team | M2 IA       |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/stream/*                              | /stream_interface/index                    | Move   | Docs Team | M2 IA       |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /interfaces/memory/*                              | /memory_interface/index                    | Move   | Docs Team | M2 IA       |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /api/cpp/interfaces/memory/transaction            | /memory_interface/transactions             | Move   | Docs Team | M2 Narrative|
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /advanced_examples/index                          | /cookbook/index                            | Link   | Docs Team | M3 Coverage |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /custom_module/index                              | /stream_interface/index                    | Move   | Docs Team | M3 Coverage |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+
| /logging/index, /pydm/index, /installing/index    | /operations/index                          | Link   | Docs Team | M1 Skeleton |
+---------------------------------------------------+--------------------------------------------+--------+-----------+-------------+

Status keys:

- Link: new section points to existing content.
- Move: narrative content moved to new canonical page.
- Split: existing page split into conceptual/how-to/reference pages.

Deferred API Reorg Notes
========================

- Reorganize the Python API section so ``Model`` and model subclasses have a
  dedicated grouped entry/page set (tracked for later milestone work).
