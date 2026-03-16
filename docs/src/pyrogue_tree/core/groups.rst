.. _pyrogue_tree_node_groups:

======
Groups
======

PyRogue groups are string tags attached to each Node (Device, Variable, Command, etc.).
They are intentionally open-ended: users can define any custom group name and use it with
``incGroups`` / ``excGroups`` filters.

How group filtering works
=========================

Most tree APIs that accept ``incGroups`` and ``excGroups`` use the same logic:

* Include check passes when ``incGroups`` is empty, or the Node is in at least one include group
* Exclude check passes when ``excGroups`` is empty, or the Node is in none of the exclude groups
* A Node is processed only if both checks pass

Built-in group names and behavior
=================================

The following names have built-in meaning in the current PyRogue implementation:

* ``Hidden``

  * Added automatically when ``hidden=True`` is used in Node constructors.
  * Used by GUI and helper defaults to hide Nodes unless explicitly included.

* ``NoConfig``

  * Excluded by Root configuration APIs/Commands such as ``SaveConfig``, ``LoadConfig``,
    ``SetYamlConfig``, and ``GetYamlConfig``.
  * Use for runtime/status items that should not be persisted as configuration.

* ``NoState``

  * Excluded by Root state-export APIs/Commands such as ``SaveState`` and ``GetYamlState``.
  * Use for values that should not be captured in state snapshots.

* ``NoStream``

  * Excluded by default in Variable streaming interfaces. E.g. pyrogue.interfaces.stream.Variable.
  * Use for Nodes that should not appear in stream output.
  * Typically used to prevent Variable logging from being set to a StreamWriter.

* ``NoSql``

  * Excluded by default in SQL logging interfaces.
  * Use for Nodes that should not be recorded in SQL logs.

* ``NoServe``

  * Excluded from served remote Node lists (for example ZMQ/virtual tree exposure).
  * Use for Nodes that should remain local-only and not be exposed remotely.

* ``Enable``

  * Used by the built-in EnableVariable class as a semantic label.
  * This is a convention used by framework components, not a hard filter category by itself.
  * Should not be used for any other purpose.

Other names you may see
=======================

* ``NoAlarm`` appears in examples/tutorial content, but there is no core framework behavior
  tied to this name in the current codebase. Treat it as a project-level convention unless
  your application defines logic for it.

Best practices
==============

* Keep built-in names for their existing semantics.
* Add project-specific groups for your own workflows (for example deployment phases, GUI views, ownership).
* Document custom groups near your Root/Device definitions so downstream users know how to filter them.
* Prefer ``incGroups`` / ``excGroups`` in bulk operations instead of ad-hoc per-Node conditionals.
