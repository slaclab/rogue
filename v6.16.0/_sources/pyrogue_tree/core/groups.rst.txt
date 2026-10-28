.. _pyrogue_tree_node_groups:

======
Groups
======

PyRogue groups are string tags attached to ``Node`` objects such as
``Device``, ``Variable``, and ``Command``. They are used to filter bulk
operations, logging, streaming, remote exposure, and other workflows that need
to act on one subset of the tree but not another.

The group model is intentionally open-ended. PyRogue defines a few names with
framework meaning, but applications are free to add project-specific group
names for their own workflows.

What Groups Are For
===================

Groups let a tree carry workflow policy directly on the Nodes it exposes.

That is useful when the same tree needs to support different views or actions,
for example:

* Configuration save and load versus live runtime state
* Stream or SQL logging versus local-only values
* Operator-facing views versus internal helper Nodes
* Project-specific subsets such as commissioning-only or debug-only controls

This is why groups appear throughout PyRogue APIs as ``incGroups`` and
``excGroups`` filters. Instead of hard-coding per-Node rules in every bulk
operation, the operation can ask the tree which Nodes belong in the requested
workflow.

How Group Filtering Works
=========================

Most tree APIs that accept ``incGroups`` and ``excGroups`` use the same basic
rule:

* If ``incGroups`` is empty, the include check passes by default.
* If ``incGroups`` is set, the Node must be in at least one of those groups.
* If ``excGroups`` is empty, the exclude check passes by default.
* If ``excGroups`` is set, the Node must be in none of those groups.

A Node is processed only if both checks pass.

In the implementation, group membership is simple set-style string matching.
There is no special hierarchy inside the group names themselves.

Built-In Group Names
====================

A small set of group names have established framework meaning in the current
implementation.

``Hidden``
----------

Added automatically when a Node is constructed with ``hidden=True``.

This is the main presentation-oriented group. GUI and helper defaults commonly
exclude ``Hidden`` Nodes unless the user explicitly asks to include them.

``NoConfig``
------------

Used for Nodes that should be excluded from configuration save and load
workflows.

In practice, Root-level configuration commands such as ``SaveConfig``,
``LoadConfig``, ``SetYamlConfig``, and ``GetYamlConfig`` exclude this group by
default. Use it for runtime-only or status-oriented values that should not be
persisted as configuration.

``NoState``
-----------

Used for Nodes that should be excluded from state snapshots or state-export
workflows.

In practice, Root-level state-export commands such as ``SaveState`` and
``GetYamlState`` exclude this group by default. Use it for values that are
transient, local-only, or otherwise not meaningful to capture in a saved state
image.

``NoStream``
------------

Used by Variable streaming workflows to suppress Nodes from the default stream
output.

In practice, Variable streaming interfaces exclude this group by default. Use
it when a Node should remain in the tree but should not be emitted through the
normal Variable stream path.

This is commonly used to prevent internal or low-value Variables from being
sent to stream-based logging or recording paths.

``NoSql``
---------

Used by SQL logging workflows to suppress Nodes from default SQL logging.

Use it for values that would add noise, have little long-term value, or should
not be recorded in that logging path.

``NoServe``
-----------

Used for Nodes that should not be exposed through served remote views such as
ZMQ or virtual-tree interfaces.

In practice, served remote-node lists exclude this group by default. Use it for
local-only controls or internal Nodes that should remain present in the process
but not be published outward.

``Enable``
----------

Used by the built-in enable-variable pattern as a semantic label. It is better
treated as a framework convention than as a general-purpose workflow filter,
and it should not be reused for unrelated meanings.

This is a convention used by framework components, not a hard filter category
by itself.

Custom Groups In Practice
=========================

Application-specific groups are often the most useful ones day to day.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='BiasTrim',
               mode='RW',
               offset=0x00,
               bitSize=16,
               groups=['Commissioning'],
           ))

           self.add(pr.RemoteVariable(
               name='DebugCounter',
               mode='RO',
               offset=0x04,
               bitSize=32,
               groups=['Debug', 'NoConfig', 'NoState'],
           ))

With that structure, bulk workflows can include or exclude those Nodes without
hard-coding special cases into every command or script.

Group Assignment Notes
======================

Groups are stored directly on each ``Node`` as strings.

Two practical details matter:

* Passing ``groups=...`` during construction assigns the initial group list.
* Calling ``addToGroup()`` on a Node propagates that group to its children.

That propagation behavior is useful when an entire subtree should participate
in one workflow policy.

Other Names You May See
=======================

``NoAlarm`` appears in some examples and project code, but there is no core
framework behavior tied to that name in this repository. Treat it as a
project-level convention unless your application defines logic for it.

Design Guidance
===============

Good group usage is usually straightforward:

* Keep the built-in names aligned with their established semantics.
* Add project-specific groups when they clearly represent a real workflow or
  view.
* Document custom groups near the ``Root`` or ``Device`` definitions that rely
  on them.
* Prefer ``incGroups`` and ``excGroups`` over ad hoc per-Node conditionals in
  bulk operations.

What To Explore Next
====================

* Root workflows that use group filters: :doc:`/pyrogue_tree/core/root`
* Variable presentation and group metadata: :doc:`/pyrogue_tree/core/variable`
* YAML configuration and state export filters: :doc:`/pyrogue_tree/core/yaml_configuration`

API Reference
=============

See :doc:`/api/python/pyrogue/node` for generated API details on ``Node``
group properties and helpers.
