.. _pyrogue_tree_root_yaml_configuration:

==================
YAML Configuration
==================

PyRogue supports configuration and state import/export through YAML APIs on
``Device`` (inherited by ``Root``) and through subtree export on ``Node``.

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
* ``Device.saveYaml(...)`` to write YAML to a file, with optional auto-naming.
* ``Device.loadYaml(...)`` to read YAML from one or more files or directories.
* ``Device.setYaml(...)`` to apply YAML text directly.

Because ``Root`` extends ``Device``, all of these methods are available on Root
as well. Root adds ``InitAfterConfig`` behavior after ``loadYaml`` and
``setYaml`` calls.

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

``Node.getYaml(...)`` and ``Device.saveYaml(...)`` both serialize current tree
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

``Device.loadYaml(...)`` accepts more than a single file path. In the current
implementation, the input can be:

* A single ``.yml`` or ``.yaml`` file.
* A directory, in which case all ``.yml`` and ``.yaml`` files in that
  directory are loaded in sorted order.
* A zip-file subdirectory path, using the same sorted-order rule on the
  matching member names in that directory.
* A Python list of those entries.
* A comma-separated string of entries.

``Device.setYaml(...)`` applies YAML text directly without going through the
filesystem.

YAML content is parsed through :func:`pyrogue.yamlToData`, so the same
``!include`` handling is available during ``loadYaml(...)`` as when parsing
YAML directly. Relative includes are resolved relative to the file being read.

For directory-like inputs, "sorted order" means an ascending lexicographic sort
of the full path strings being loaded. For one directory, that is effectively
lexicographic filename order. For example:

* ``00-defaults.yml``
* ``10-overrides.yml``

load in that order, so later files can intentionally override earlier values.

For ``loadYaml(..., writeEach=False)`` and ``setYaml(..., writeEach=False)``,
the application workflow is:

1. Parse YAML input to ordered dictionaries.
2. Traverse the tree and assign Variable display values with
   ``setDisp(..., write=False)``.
3. After the full YAML payload is staged in shadow state, commit through the
   device's write path (``writeBlocks``, ``verifyBlocks``, ``checkBlocks``).

Implications:

* If a Variable is assigned more than once while loading, the last assignment
  wins in shadow memory before commit
* Hardware is not touched until the bulk commit step
* For directory and zip-directory loads, "last assignment wins" follows the
  lexicographic file/member order described above
* For explicit Python lists or comma-separated file lists, it follows the
  order you passed to ``loadYaml(...)``

If ``writeEach=True``, each ``setDisp`` write is issued immediately while YAML
is being traversed (no final consolidated write pass). That means later YAML
entries can still overwrite earlier values, but the intermediate hardware writes
have already occurred.

The load path is wrapped in both ``Root.pollBlock()`` and ``Root.updateGroup()``
so polling does not race with the configuration operation and listeners see a
coalesced update batch.

For zip-file subdirectory loads, only YAML files in the immediate requested
directory are considered. Nested subdirectories are ignored, matching the
normal directory behavior.

The staged values are then committed using the normal tree transaction path.
For the bulk write, verify, read, and check model behind that commit step, see
:doc:`/pyrogue_tree/core/block_operations`.

Device-Level YAML Operations
=============================

Any ``Device`` in the tree can load, save, or apply YAML directly. This allows
configuration of individual devices without needing to know the full tree
structure.

**Device-level YAML format** uses the device name or child names as top-level
keys (not absolute paths like ``root.Top.Child``):

.. code-block:: yaml

   # Load on a device named "MyDevice"
   MyDevice:
     Variable1: 10
     SubDevice:
       Variable2: 20

Or target children directly:

.. code-block:: yaml

   # Load on "MyDevice" — keys are children
   Variable1: 10
   SubDevice:
     Variable2: 20

Device-level loads support the same array matching and wildcard syntax:

.. code-block:: yaml

   # Load on a device with array children
   Channel[*]:
     Gain: 100

**Device-level writes are scoped** to the device subtree. Only blocks belonging
to the device and its descendants are written, verified, and checked. The
``ForceWrite`` setting on Root is still respected.

**Round-trip example:**

.. code-block:: python

   with root:
       # Save config from a specific device
       root.MyBoard.saveYaml(
           name="board_config.yml",
           readFirst=True,
           modes=["RW", "WO"],
           excGroups="NoConfig",
       )

       # Load it back on the same device
       root.MyBoard.loadYaml(
           name="board_config.yml",
           writeEach=False,
           modes=["RW", "WO"],
           excGroups="NoConfig",
       )

**Root-level loading** continues to use absolute dotted paths
(``root.Top.Child``) for backward compatibility. The path resolution strategy
depends on which level ``loadYaml`` is called:

* On ``Root``: top-level YAML keys are resolved as absolute paths via
  ``Root.getNode()``.
* On ``Device``: top-level YAML keys are resolved as the device name or
  direct children via ``nodeMatch()``.

Practical Guidance
==================

* Separate baseline configuration from transient runtime state.
* Track YAML files in source control when they represent release artifacts.
* Document version compatibility when tree names or meaning change.
* Prefer ``writeEach=False`` for coordinated configuration loads unless you
  specifically need immediate per-entry writes.
* Use device-level ``loadYaml`` when configuring individual subsystems to
  avoid coupling YAML files to the full tree structure.

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
* ``InitAfterConfig``: call ``initialize()`` after config apply (Root-level
  ``loadYaml`` and ``setYaml`` only)

What To Explore Next
====================

* Root lifecycle and built-in commands: :doc:`/pyrogue_tree/core/root`
* Group filtering semantics: :doc:`/pyrogue_tree/core/groups`
* Device block traversal and commit behavior: :doc:`/pyrogue_tree/core/block_operations`
* Device-level configuration: :doc:`/pyrogue_tree/core/device`

Related Topics
==============

* Polling behavior during bulk operations: :doc:`/pyrogue_tree/core/poll_queue`
