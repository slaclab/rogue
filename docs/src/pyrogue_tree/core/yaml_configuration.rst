.. _pyrogue_tree_root_yaml_configuration:

==================
YAML Configuration
==================

PyRogue supports configuration and state import/export through YAML APIs on
``Root`` and through subtree export on ``Node``.

These APIs are the standard way to capture a known-good configuration, restore
it later, or inspect the current tree as structured YAML rather than as
interactive Variables.

Typical YAML Workflows
======================

* Configuration baselines for known-good startup values
* Captured runtime state for debug and issue reproduction
* Status snapshots for validation and operator handoff

Main Entry Points
=================

The main YAML entry points are:

* ``Node.getYaml(...)`` to export one subtree as YAML text.
* ``Root.saveYaml(...)`` to write YAML to a file, with optional auto-naming.
* ``Root.loadYaml(...)`` to read YAML from one or more files or directories.
* ``Root.setYaml(...)`` to apply YAML text directly.

These APIs also back the built-in hidden Root commands:

* ``SaveConfig`` / ``LoadConfig``
* ``SaveState``
* ``SetYamlConfig`` / ``GetYamlConfig`` / ``GetYamlState``

The command wrappers mainly pre-select useful defaults for modes and group
filters.

Configuration Vs State Filters
==============================

Typical defaults:

* Config operations use modes ``['RW', 'WO']`` and exclude ``NoConfig``
* State operations use modes ``['RW', 'RO', 'WO']`` and exclude ``NoState``

That means:

* Read-only Variables are normally ignored for config load
* Commands are ignored by YAML set/load (``BaseCommand._setDict`` is a no-op)

This is why configuration YAML usually reads like "things you can set", while
state YAML reads like "everything worth observing".

Saving YAML
===========

``Node.getYaml(...)`` and ``Root.saveYaml(...)`` both serialize current tree
values using the same underlying tree-dictionary path.

Important export options:

* ``readFirst=True`` performs a Root-wide read before export.
* ``modes`` controls which Variable access modes are included.
* ``incGroups`` and ``excGroups`` apply the same group-filtering model used
  elsewhere in the tree.
* ``recurse`` on ``getYaml(...)`` controls whether child Devices are included.

``saveYaml(...)`` can either write to a named file or auto-generate a
timestamped filename. If the target name ends in ``.zip``, it writes the YAML
payload into a compressed zip member.

Loading And Applying YAML
=========================

``Root.loadYaml(...)`` accepts more than a single file path. In the current
implementation, the input can be:

* A single ``.yml`` or ``.yaml`` file.
* A directory, in which case all ``.yml`` and ``.yaml`` files in that
  directory are loaded in sorted order.
* A zip-file subdirectory path.
* A Python list of those entries.
* A comma-separated string of entries.

``Root.setYaml(...)`` applies YAML text directly without going through the
filesystem.

For ``loadYaml(..., writeEach=False)`` and ``setYaml(..., writeEach=False)``,
the application workflow is:

1. Parse YAML input to ordered dictionaries.
2. Traverse the tree and assign Variable display values with
   ``setDisp(..., write=False)``.
3. After the full YAML payload is staged in shadow state, run the normal Root
   configuration-commit path through ``Root._write()``.

Implications:

* If a Variable is assigned more than once while loading, the last assignment
  wins in shadow memory before commit
* Hardware is not touched until the bulk commit step

If ``writeEach=True``, each ``setDisp`` write is issued immediately while YAML
is being traversed (no final consolidated ``Root._write()`` pass).

The load path is wrapped in both ``Root.pollBlock()`` and ``Root.updateGroup()``
so polling does not race with the configuration operation and listeners see a
coalesced update batch.

The staged values are then committed using the normal tree transaction path.
For the bulk write, verify, read, and check model behind that commit step, see
:doc:`/pyrogue_tree/core/block_operations`.

Practical Guidance
==================

* Separate baseline configuration from transient runtime state.
* Track YAML files in source control when they represent release artifacts.
* Document version compatibility when tree names or meaning change.
* Prefer ``writeEach=False`` for coordinated configuration loads unless you
  specifically need immediate per-entry writes.

Array Matching And Slicing In YAML Keys
=======================================

YAML load supports array-style Node matching:

* ``AmcCard[0]:``
* ``AmcCard[1:3]:``
* ``AmcCard[:]:``
* ``AmcCard[*]:``

Examples:

.. code-block:: yaml

   Root:
     AmcCard[:]:
       DacEnable[0]: True

     AmcCard[1:3]:
       DacEnable: True

The matching rules follow the same array-aware ``nodeMatch()`` behavior used by
the tree:

* ``[0]`` selects one element.
* ``[:]`` and ``[*]`` select all elements.
* ``[1:3]`` uses Python-style slice semantics, so it selects elements 1 and 2.

Array Variables can also be targeted at the Variable level, for example with
``DacEnable[0]``.

Related settings on Root:

* ``ForceWrite``: force writes of non-stale Blocks in bulk config paths
* ``InitAfterConfig``: call ``initialize()`` after config apply

What To Explore Next
====================

* Root lifecycle and built-in commands: :doc:`/pyrogue_tree/core/root`
* Group filtering semantics: :doc:`/pyrogue_tree/core/groups`
* Device block traversal and commit behavior: :doc:`/pyrogue_tree/core/block_operations`

Related Topics
==============

* Polling behavior during bulk operations: :doc:`/pyrogue_tree/core/poll_queue`
