.. _pyrogue_tree_node_device:

======
Device
======

A :py:class:`~pyrogue.Device` is the primary composition unit in a PyRogue
tree. ``Device`` is where most hardware abstractions and subsystem boundaries
are expressed: devices hold child Devices, Variables, and Commands, and they
also participate in the memory-routing and block-traversal behavior that backs
hardware access.

If ``Root`` is the application owner, ``Device`` is the structural unit that
turns the application into an organized tree.

That relationship is literal in the implementation: :py:class:`~pyrogue.Root`
inherits from :py:class:`~pyrogue.Device`. This matters because the top of the
tree uses the same composition and traversal model as every other Device, while
adding the extra lifecycle and application-level behavior described on the
``Root`` page.

What A Device Does
==================

A ``Device`` usually serves two roles at once:

* It groups related Nodes into a coherent modular subtree.
* It provides the address and transaction context that hardware-backed
  Variables use for block operations.

That means a Device is not just a folder-like container. It is also part of the
runtime path for reads, writes, resets, and startup behavior.

Typical contents of a Device:

* Child ``Device`` instances for hierarchical composition.
* ``Variable`` Nodes for telemetry and configuration.
* ``Command`` Nodes for actions and procedures.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(description='Example device', **kwargs)

           self.add(pr.LocalVariable(
               name='Mode',
               mode='RW',
               value=0,
           ))

           self.add(pr.LocalCommand(
               name='Reset',
               function=self._reset,
           ))

       def _reset(self):
           pass

The important design question at Device scope is usually, "What belongs in one
subtree?" Good Device boundaries often follow hardware blocks, functional
subsystems, or operator-facing units of control.

Key Device Properties
=====================

Common Device-level properties include:

* ``offset`` for placing the Device within the parent memory address space.
* ``memBase`` for the memory interface used by hardware-backed children.
* ``enable`` for controlling whether the subtree participates in hardware
  access behavior.
* ``forceCheckEach`` for forcing block reads, writes, and verifies to check
  each transaction immediately rather than deferring completion checks.

The built-in ``enable`` Variable is especially important because it lets a tree
keep its full structure visible while disabling hardware interaction for one
subtree.

Composition And Tree Structure
==============================

Most PyRogue trees are built by defining Device subclasses and nesting them.
That makes ``Device.add(...)`` one of the central APIs in day-to-day PyRogue
work.

In practice:

* ``Root`` defines the top of the hierarchy.
* Top-level Devices partition the design into major subsystems.
* Child Devices refine that structure until Variables and Commands sit at the
  right operational boundary.

That pattern is why the readability of the tree matters. A good Device layout
is not only easier to maintain in code; it also produces clearer paths, clearer
PyDM navigation, and better remote-client ergonomics.

For repeated register layouts, :py:meth:`~pyrogue.Device.addRemoteVariables`
can define an indexed set of ``RemoteVariable`` entries from one call. When
used with ``pack=True``, PyRogue keeps the indexed array container at the base
name and also adds a packed :py:class:`~pyrogue.LinkVariable` at
``<name>_All``. That packed alias joins element display values with
underscores in reverse index order, which is useful when several orthogonal
fields also need to be exposed as one combined value.

Managed Interfaces And Protocol Ownership
=========================================

Devices can also own helper objects that need coordinated runtime startup and
shutdown. The standard way to register those objects is
:py:meth:`~pyrogue.Device.addInterface`, which also has the alias
:py:meth:`~pyrogue.Device.addProtocol`.

Typical managed objects include:

* Rogue memory or stream interfaces.
* Protocol servers or clients.
* Custom helpers that implement ``_start()`` and/or ``_stop()``.

At runtime:

* :py:meth:`~pyrogue.Device._start` calls ``_start()`` on registered objects if
  the method exists.
* :py:meth:`~pyrogue.Device._stop` calls ``_stop()`` on registered objects if
  the method exists.
* Both methods then recurse into child Devices.

This is why top-level interfaces are commonly registered on ``Root``:
``Root`` is itself a ``Device``, so it participates in the same managed
interface lifecycle.

There is not yet a separate page dedicated to this lifecycle. For the Root side
of the same startup and shutdown behavior, see :doc:`/pyrogue_tree/core/root`.

Device Lifecycle Hooks
======================

Most Device subclasses are created entirely in ``__init__``, but there are a
few important lifecycle hooks for behavior that depends on tree attachment or a
running system context.

Attachment And Startup Order
----------------------------

During :py:meth:`~pyrogue.Root.start`, Device lifecycle progresses in this
order:

#. :py:meth:`~pyrogue.Device._rootAttached`
#. :py:meth:`~pyrogue.Node._finishInit`
#. :py:meth:`~pyrogue.Device._start`

During :py:meth:`~pyrogue.Root.stop`, Root calls
:py:meth:`~pyrogue.Device._stop` recursively.

What Each Hook Is For
---------------------

* :py:meth:`~pyrogue.Device._rootAttached`

  Use this for structure-dependent setup that requires valid ``root``,
  ``parent``, or path context. This is also when Device Block (memory) layout is built.
  During this step, the Device walks its Variables, groups compatible
  hardware-backed Variables into ``Block`` objects, attaches any pre-created
  custom Blocks, and records the Block structure that later bulk operations
  traverse.

* :py:meth:`~pyrogue.Node._finishInit`

  Use this sparingly for final initialization that depends on the attached
  hierarchy. Most Device subclasses do not need to override it.

* :py:meth:`~pyrogue.Device._start`

  Use this for runtime startup work such as enabling subscriptions, opening
  services, or starting Device-owned threads.

* :py:meth:`~pyrogue.Device._stop`

  Use this for runtime teardown and resource cleanup.

The practical rule is simple: use ``__init__`` for static tree construction,
use ``_rootAttached`` for attach-time structure work, and use ``_start`` and
``_stop`` for live runtime behavior.

.. _pyrogue_tree_node_device_managed_interfaces:

Example: Runtime Work In ``_start()`` And ``_stop()``
-----------------------------------------------------

.. code-block:: python

   import pyrogue as pr
   import threading
   import time

   class WorkerDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self._runWorker = False
           self._workerThread = None

       def _start(self):
           super()._start()
           self._runWorker = True
           self._workerThread = threading.Thread(target=self._worker, daemon=True)
           self._workerThread.start()

       def _stop(self):
           self._runWorker = False
           if self._workerThread is not None:
               self._workerThread.join(timeout=1.0)
           super()._stop()

       def _worker(self):
           while self._runWorker:
               time.sleep(0.1)

Foundational Transaction Operations
===================================

``Device`` is where the PyRogue tree's foundational hardware transaction
operations come together. At this level, four ideas matter:

* ``write`` sends staged values from the tree toward hardware.
* ``verify`` checks that hardware matches the expected value after a write.
* ``read`` fetches current hardware state back into the tree.
* ``check`` waits for initiated transactions to complete and surfaces errors.

Those operations are foundational because they are reused throughout the tree:
bulk configuration, per-Variable access, YAML apply paths, and many custom
hardware procedures all build on the same model.

One PyRogue design choice is especially important here: transaction initiation
is intentionally separated from completion. ``write``, ``verify``, and
``read`` start work, while ``check`` is the step that waits for the
responses. That separation lets a ``Device`` issue many operations first and
then retire them as a group.

Posted writes also exist in PyRogue, but they are usually exposed through
per-Variable ``post()`` methods and posted ``RemoteCommand`` helpers rather
than as a foundational full-Device traversal API.

Device-Level Block APIs
=======================

``Device`` is where those operations become tree traversal methods. Device-level
block APIs traverse the tree and issue transactions for the ``Block`` objects
attached to that Device and, optionally, its children.

The main methods are:

* :py:meth:`~pyrogue.Device.writeBlocks`
* :py:meth:`~pyrogue.Device.verifyBlocks`
* :py:meth:`~pyrogue.Device.readBlocks`
* :py:meth:`~pyrogue.Device.checkBlocks`

At a high level:

* ``writeBlocks`` initiates write transactions.
* ``verifyBlocks`` initiates verify transactions.
* ``readBlocks`` initiates read transactions.
* ``checkBlocks`` waits for previously initiated transactions to complete.

All four methods can operate on the full Device subtree or on the Block backing
one specific Variable, and they are the normal override points when hardware
requires custom sequencing.

If a Device should always use stricter transaction-by-transaction completion
checking, set ``self.forceCheckEach = True`` in the subclass. That causes the
Device-level block methods to behave as though ``checkEach=True`` had been
requested on each call.

For the detailed traversal model, ordering rules, and single-Variable versus
full-subtree behavior, see :doc:`/pyrogue_tree/core/block_operations`.

Where These Methods Fit
-----------------------

These methods are often used indirectly rather than called manually.

Common examples:

* :py:meth:`~pyrogue.RemoteVariable.set` uses Device block-write paths for
  hardware-backed writes.
* :py:meth:`~pyrogue.RemoteVariable.get` uses Device block-read paths for
  hardware-backed reads.
* Root-level YAML and bulk commands call recursive Device block operations
  across the tree.

That is why Device block methods are the normal extension point when hardware
requires custom sequencing.

Custom Sequencing
-----------------

Override the block APIs when hardware access requires more than the default
tree traversal. Common reasons include:

* Required pre- or post-register writes.
* Paged or banked register windows.
* Commit or strobe registers that must be pulsed around updates.
* Custom ordering across child Devices.

.. code-block:: python

   class SequencedDevice(pyrogue.Device):
       def writeBlocks(self, *, force=False, recurse=True, variable=None, checkEach=False, index=-1):
           # Pre-transaction behavior.
           super().writeBlocks(
               force=force,
               recurse=recurse,
               variable=variable,
               checkEach=checkEach,
               index=index,
           )
           # Post-transaction behavior.

For the lower-level transaction and grouping model behind those APIs, see
:doc:`/pyrogue_tree/core/block` and
:doc:`/pyrogue_tree/core/block_operations`.

Relationship To The Memory Hub Model
====================================

Under the hood, ``pyrogue.Device`` participates in the Rogue memory hub stack.
Conceptually, a Device behaves like a Hub:

* Block transactions are addressed relative to the Device base.
* Child Devices can inherit the parent's routing context.
* A child Device can also be attached to a different memory path when needed.

That is the reason Device composition and transaction behavior are so closely
linked in PyRogue. Tree structure and hardware-access structure are related,
even though they are not always identical.

For deeper memory-stack behavior, see:

* :doc:`/pyrogue_tree/core/block`
* :doc:`/memory_interface/index`

Operational Hooks And Decorators
================================

In addition to startup and block sequencing hooks, Device subclasses commonly
override operational hooks such as:

* :py:meth:`~pyrogue.Device.initialize`
* :py:meth:`~pyrogue.Device.hardReset`
* :py:meth:`~pyrogue.Device.countReset`
* :py:meth:`~pyrogue.Device.enableChanged`

These support system-level workflows invoked from Root commands or from custom
application logic.

Device also supports decorators that create :py:class:`~pyrogue.LocalCommand`
Nodes from local functions.

.. code-block:: python

   @pyrogue.command(name='ReadConfig', value='', description='Load config file')
   def _readConfig(self, arg):
       self.root.loadYaml(name=arg, writeEach=False, modes=['RW', 'WO'])

What To Explore Next
====================

* Variable behavior and type choices: :doc:`/pyrogue_tree/core/variable`
* Command behavior and invocation: :doc:`/pyrogue_tree/core/command`
* Block transaction behavior: :doc:`/pyrogue_tree/core/block`
* Built-in Device catalog: :doc:`/pyrogue_tree/builtin_devices/index`

API Reference
=============

See :doc:`/api/python/pyrogue/device` for generated API details.
