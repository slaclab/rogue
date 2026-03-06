.. _pyrogue_tree_core:
.. _pyrogue_tree_node:

====
Core
====

The Core layer defines the object model and runtime behavior of a PyRogue tree.
It organizes control logic into a hierarchy of ``Root``, ``Device``,
``Variable``, and ``Command`` nodes, with ``Block`` and ``Model`` providing
memory transaction grouping and typed value conversion.

A typical hierarchy starts at one ``Root`` and fans into multiple ``Device``
subtrees. Each Device can contain child Devices, Variables, and Commands.
At runtime, the Root coordinates startup, background polling, and system-wide
read/write operations across that hierarchy.

Minimal tree example
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
and ``Variable``/``Command`` nodes expose state and actions.

Core Node model
===============

``Node`` is the common base class for the full tree object model.
Every ``Root``, ``Device``, ``Variable``, and ``Command`` inherits shared
identity and hierarchy behavior (name/path/root/parent relationships).

Core responsibilities include:

* stable hierarchical addressing and lookup
* group tagging/filtering support
* lifecycle attachment to a Root context
* shared logging/path conventions across all subclasses

Concrete node categories
========================

* :ref:`pyrogue_tree_node_root`
* :ref:`pyrogue_tree_node_device`
* :ref:`pyrogue_tree_node_command`
* :ref:`pyrogue_tree_node_variable`
* :ref:`pyrogue_tree_node_block`
* :ref:`pyrogue_tree_node_groups`

Common design workflow
======================

1. Define one ``Root`` for lifecycle, top-level interfaces, and system actions.
2. Partition the design into ``Device`` subtrees by hardware/function boundary.
3. Add ``Variable`` and ``Command`` nodes for control and telemetry procedures.
4. Confirm memory mapping/transaction behavior through ``Block`` and ``Model``.
5. Expose remote access patterns for GUIs, scripts, notebooks, and clients.

Where to explore next
=====================

* Root lifecycle and orchestration: :doc:`/pyrogue_tree/core/root/index`
* Device composition and managed interfaces: :doc:`/pyrogue_tree/core/device/index`
* Variable behavior and types: :doc:`/pyrogue_tree/core/variable/index`
* Block transaction behavior: :doc:`/pyrogue_tree/core/blocks`
* Model conversion behavior: :doc:`/pyrogue_tree/core/model`

.. toctree::
   :maxdepth: 2
   :caption: Core:

   root/index
   root/poll_queue
   root/yaml_configuration
   device/index
   command/index
   variable/index
   groups
   model
   blocks
