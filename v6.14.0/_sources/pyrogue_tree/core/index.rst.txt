.. _pyrogue_tree_core:
.. _pyrogue_tree_node:

.. Follow-up doc gap: add dedicated coverage for the Variable Update mechanism.

=====================================
PyRogue Tree Components And Concepts
=====================================

A PyRogue tree is defined by the object model and runtime behavior of
``Root``, ``Device``, ``Variable``, and ``Command`` Nodes, with ``Block`` and
``Model`` providing memory transaction grouping and typed value conversion.

A typical hierarchy starts at one ``Root`` and fans into multiple ``Device``
subtrees. Each ``Device`` can contain child ``Device`` Nodes, ``Variable``
Nodes, and ``Command`` Nodes. At runtime, the ``Root`` coordinates startup,
background polling, and system-wide read/write operations across that
hierarchy.

This subsection is intentionally split into foundational pages first and more
specialized mechanics later. Most readers should understand ``Root``,
``Device``, ``Variable``, and ``Command`` before diving into ``Block``,
``Model``, polling internals, YAML bulk configuration, or stream adapters.

Minimal Tree Example
====================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.interfaces

   class DemoDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.LocalVariable(
               name='Enable',
               mode='RW',
               value=False,
           ))

           self.add(pr.LocalCommand(
               name='Reset',
               function=lambda: print('Reset requested'),
           ))

   class DemoRoot(pr.Root):
       def __init__(self):
           super().__init__(name='DemoRoot', pollEn=False)

           self.add(DemoDevice(name='App'))

           # Optional: expose the running tree to remote clients.
           self.addInterface(pyrogue.interfaces.ZmqServer(
               root=self,
               addr='127.0.0.1',
               port=0,
           ))

This composition pattern is the foundation for most PyRogue applications:
``Root`` owns lifecycle, ``Device`` organizes hardware/application structure,
and ``Variable``/``Command`` Nodes expose state and actions.

How To Read This Subsection
===========================

Use the core pages in this order:

1. ``Root`` for lifecycle, startup, and whole-tree control behavior.
2. ``Device`` for composition, interface ownership, and block traversal.
3. ``Variable`` and ``Command`` for the two main leaf-node interaction models.
4. The subtype pages for local, remote, and link variants.
5. The more advanced mechanics pages once the tree model itself is familiar.

That ordering keeps the conceptual model stable before introducing the details
of memory grouping, typed encoding, polling internals, and YAML bulk
configuration.

Core Node Model
===============

``Node`` is the common base class for the full tree object model.
Every ``Root``, ``Device``, ``Variable``, and ``Command`` inherits shared
identity and hierarchy behavior (name/path/root/parent relationships).

The shared responsibilities of ``Node``-derived types include:

* Stable hierarchical addressing and lookup
* Group tagging/filtering support
* Lifecycle attachment to a Root context
* Shared logging/path conventions across all subclasses

Concrete Node Categories
========================

* :ref:`pyrogue_tree_node_root`
* :ref:`pyrogue_tree_node_device`
* :ref:`pyrogue_tree_node_variable`
* :ref:`pyrogue_tree_node_command`
* :ref:`pyrogue_tree_node_block`
* :ref:`pyrogue_tree_node_groups`

Common Design Workflow
======================

1. Define one ``Root`` for lifecycle, top-level interfaces, and system actions.
2. Partition the design into ``Device`` subtrees by hardware/function boundary.
3. Add ``Variable`` and ``Command`` Nodes for control and telemetry procedures.
4. Choose local, remote, or linked Node subtypes as needed.
5. Confirm memory mapping and typed conversion behavior through ``Block`` and
   ``Model``.
6. Expose remote access patterns for GUIs, scripts, notebooks, and clients.

Advanced Topics And Why They Are Separate
=========================================

Some pages in this subsection are deliberately separated because they describe
mechanics that matter a lot in real systems, but are usually not the right
starting point:

* ``Block`` is about transaction grouping and memory access flow.
* ``Device Block Operations`` is about recursive ``Device`` traversal and
  sequencing of the ``*Blocks`` methods.
* ``Model`` is about typed byte conversion and custom encodings.
* ``Fixed-Point Models`` is a focused companion page for ``Fixed`` and
  ``UFixed`` usage.
* ``Floating Point Types Summary`` is a quick-reference table for GPU-oriented
  float formats and NVIDIA architecture support.
* ``Poll Queue`` is about background scheduling behavior.
* ``YAML Configuration`` is about YAML save/load workflows, matching rules,
  and configuration file structure.
* ``Memory Variable Stream`` is about bridging variable updates into stream
  processing paths.
* ``Groups`` is about filtering and bulk-operation scoping.

Those topics belong in core because they define how the tree behaves, but they
are advanced enough that they read better as focused pages rather than as long
detours inside the introductory ``Root``/``Device``/``Variable`` docs.

What To Explore Next
====================

* Root lifecycle and orchestration: :doc:`/pyrogue_tree/core/root`
* Device composition and managed interfaces: :doc:`/pyrogue_tree/core/device`
* Variable behavior and types: :doc:`/pyrogue_tree/core/variable`
* Command behavior and invocation patterns: :doc:`/pyrogue_tree/core/command`
* Block transaction behavior: :doc:`/pyrogue_tree/core/block`
* Device block traversal and sequencing: :doc:`/pyrogue_tree/core/block_operations`
* Model conversion behavior: :doc:`/pyrogue_tree/core/model`
* Fixed-point model details: :doc:`/pyrogue_tree/core/fixed_point_models`
* Poll scheduling behavior: :doc:`/pyrogue_tree/core/poll_queue`
* YAML save/load behavior: :doc:`/pyrogue_tree/core/yaml_configuration`
* Variable-to-stream adapter behavior: :doc:`/pyrogue_tree/core/memory_variable_stream`

API Reference
=============

- Python:
  :doc:`/api/python/pyrogue/root`,
  :doc:`/api/python/pyrogue/device`,
  :doc:`/api/python/pyrogue/basevariable`,
  :doc:`/api/python/pyrogue/basecommand`,
  :doc:`/api/python/pyrogue/model`

.. toctree::
   :maxdepth: 2
   :caption: Core:

   root
   device
   variable
   command
   block
   block_operations
   model
   fixed_point_models
   float_types_summary
   poll_queue
   yaml_configuration
   memory_variable_stream
   groups
