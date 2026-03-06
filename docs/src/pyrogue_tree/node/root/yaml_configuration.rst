.. _pyrogue_tree_root_yaml_configuration:

==============================
YAML Configuration and Bulk IO
==============================

PyRogue supports configuration/state import and export through YAML APIs on
``Root``.

Main entry points
=================

- ``saveYaml(...)``: write YAML to file/zip from current tree values
- ``loadYaml(...)``: read YAML from file(s)/directory and apply to tree
- ``setYaml(...)``: apply YAML text directly
- ``getYaml(...)``: generate YAML text for a node/tree

Root commands exposed in the tree use these APIs:

- ``SaveConfig`` / ``LoadConfig``
- ``SaveState``
- ``SetYamlConfig`` / ``GetYamlConfig`` / ``GetYamlState``

Config vs state filters
=======================

Typical defaults:

- config operations use modes ``['RW', 'WO']`` and exclude ``NoConfig``
- state operations use modes ``['RW', 'RO', 'WO']`` and exclude ``NoState``

That means:

- read-only variables are normally ignored for config load
- commands are ignored by YAML set/load (``BaseCommand._setDict`` is a no-op)

How YAML load is applied
========================

For ``loadYaml(..., writeEach=False)`` and ``setYaml(..., writeEach=False)``,
the workflow is:

1. Parse YAML input to ordered dictionaries.
2. Traverse tree entries and assign variable display values with
   ``setDisp(..., write=False)``.
3. After the whole YAML payload is staged in shadow values, run root bulk
   write/verify/check (``Root._write()``).

Implications:

- if a variable is assigned more than once while loading, the last assignment
  wins in shadow memory before commit
- hardware is not touched until the bulk commit step

If ``writeEach=True``, each ``setDisp`` write is issued immediately while YAML
is being traversed (no final consolidated ``Root._write()`` pass).

Commit ordering
===============

Bulk commit is queued recursively using tree/device order:

- device traversal follows tree child ordering
- each device enqueues its blocks in ``self._blocks`` order
- for auto-built blocks, ordering is typically lower-offset first because block
  creation starts from variables sorted by ``(offset, size)``

After enqueue:

- ``verify`` transactions are queued
- ``check`` phase waits for queued operations to complete and surfaces errors

In other words, PyRogue separates transaction initiation from completion. The completion/wait
step is called ``check`` in API naming.

Array matching and slicing in YAML keys
=======================================

YAML load supports array-style node matching:

- ``AmcCard[0]:``
- ``AmcCard[1:3]:``
- ``AmcCard[:]:``
- ``AmcCard[*]:``

Examples:

- ``AmcCard[:]: DacEnable[0]: True``
- ``AmcCard[1:3]: DacEnable: True``

Bulk operations: enqueue vs check
=================================

Bulk methods intentionally decouple transaction issue from wait:

- enqueue: ``writeBlocks``, ``readBlocks``, ``verifyBlocks``
- wait/check: ``checkBlocks``

This pattern allows many operations to be issued first, then checked as a
group, which reduces per-transaction blocking overhead.

``checkEach=True`` changes behavior to check completion after each block
transaction instead of deferring checks.

Related settings on Root:

- ``ForceWrite``: force writes of non-stale blocks in bulk config paths
- ``InitAfterConfig``: call ``initialize()`` after config apply

Where to explore next
=====================

- Root lifecycle/details: :doc:`/pyrogue_tree/node/root/index`
- Polling behavior: :doc:`/pyrogue_tree/node/root/poll_queue`
- Group filtering semantics: :doc:`/pyrogue_tree/node/groups`
- Device/block transaction paths: :doc:`/pyrogue_tree/node/device/index`,
  :doc:`/pyrogue_tree/node/block/index`
