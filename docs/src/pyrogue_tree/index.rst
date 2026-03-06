.. _pyrogue_tree:

============
PyRogue Tree
============

The PyRogue tree is the application-facing structure used to compose a Rogue
system. It organizes control logic into a hierarchy of ``Root``, ``Device``,
``Variable``, and ``Command`` nodes, all derived from :ref:`pyrogue_tree_node`.

The tree is intentionally independent from physical bus topology. Memory and
stream transports can be wired for performance while the tree stays focused on
clear operator-facing structure and workflow.

A typical hierarchy starts at one ``Root`` and fans into multiple ``Device``
subtrees. Each device can contain child devices, variables, and commands.
At runtime, the root coordinates startup, background polling, and system-wide
read/write operations across that hierarchy.

The tree is also the boundary where client/server interfaces are attached so
multiple clients can interact with one running system at the same time.
This enables workflows such as:

- automation scripts issuing control sequences
- Jupyter notebooks for interactive diagnostics
- GUI clients for live monitoring and operations

These clients connect to the same server-side tree and observe a consistent
device/variable/command model.
For client interface specifics, see :doc:`/pyrogue_core/client_access`.

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
           self.addInterface(pyrogue.interfaces.ZmqServer(root=self, addr='127.0.0.1', port=0))

This example introduces the basic composition pattern used throughout PyRogue:
``Root`` owns the application tree, ``Device`` organizes logic, and
``Variable``/``Command`` nodes expose state and actions.

Core Node Model
===============

``Node`` is the common base class for the full tree object model.
Every ``Root``, ``Device``, ``Variable``, and ``Command`` inherits shared
identity and hierarchy behavior (name/path/root/parent relationships).

Core responsibilities include:

- stable hierarchical addressing and lookup
- group tagging/filtering support
- lifecycle attachment to a root context
- shared logging/path conventions across all subclasses

Concrete node categories:

- :ref:`pyrogue_tree_node_root`
- :ref:`pyrogue_tree_node_device`
- :ref:`pyrogue_tree_node_command`
- :ref:`pyrogue_tree_node_variable`
- :ref:`pyrogue_tree_node_block`
- :ref:`pyrogue_tree_node_groups`

Where to explore next
=====================

- Root lifecycle and orchestration: :doc:`/pyrogue_tree/node/root/index`
- Device composition and managed interfaces: :doc:`/pyrogue_tree/node/device/index`
- Variable behavior and types: :doc:`/pyrogue_tree/node/variable/index`
- Block/model conversion internals: :doc:`/pyrogue_tree/blocks`
- Model reference overview: :doc:`/pyrogue_tree/model`

.. toctree::
   :maxdepth: 2
   :caption: PyRogue Tree:

   node/root/index
   node/root/poll_queue
   node/root/yaml_configuration
   node/device/index
   node/command/index
   node/variable/index
   model
   blocks
