.. _pyrogue_tree_node_device:

======
Device
======

Device Definition
=================

A :py:class:`~pyrogue.Device` is the primary composition unit in a PyRogue tree.
Devices can contain:

* Child Devices
* Variables (local, remote, link)
* Commands (local, remote)

Most user-facing hardware abstractions are implemented as ``Device`` subclasses.
At runtime, a Device also participates in memory routing behavior through the
Rogue memory hub stack.

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(description='Example device', **kwargs)
           self.add(pr.LocalVariable(name='Mode', mode='RW', value=0))
           self.add(pr.LocalCommand(name='Reset', function=self._reset))

       def _reset(self):
           pass

Key Attributes
--------------

In addition to inherited :ref:`Node <pyrogue_tree_node>` attributes, common
Device-level attributes include:

* ``offset`` / ``address``
* ``memBase``
* ``enable``

The ``enable`` Variable allows tree-level logic to disable a full Device subtree
for hardware access while keeping Node metadata available.

Relationship to Hub
-------------------

Conceptually, a Device behaves as a Hub in the memory routing stack:

* Variable/Block transactions are addressed relative to the Device base
* Child Devices can inherit base/memory routing from parent Devices
* A child Device can also be attached to an independent memory path when needed

Key Methods
-----------

Commonly used methods:

* :py:meth:`~pyrogue.Device.add`
* :py:meth:`~pyrogue.Device.addRemoteVariables`
* :py:meth:`~pyrogue.Device.hideVariables`
* :py:meth:`~pyrogue.Device.initialize`
* :py:meth:`~pyrogue.Device.hardReset`
* :py:meth:`~pyrogue.Device.countReset`
* :py:meth:`~pyrogue.Device.writeBlocks`
* :py:meth:`~pyrogue.Device.verifyBlocks`
* :py:meth:`~pyrogue.Device.readBlocks`
* :py:meth:`~pyrogue.Device.checkBlocks`

.. _pyrogue_tree_node_device_managed_interfaces:

Managed Interfaces: ``addInterface()`` and ``addProtocol()``
-------------------------------------------------------------

Devices can own stream/memory/protocol helper objects that need coordinated
startup/shutdown with the Device tree.

Canonical term used in this documentation:
``Managed Interface Lifecycle``.
This refers to the ``_start()`` / ``_stop()`` callback contract for objects
registered through :py:meth:`~pyrogue.Device.addInterface`.

Use :py:meth:`~pyrogue.Device.addInterface` (or alias
:py:meth:`~pyrogue.Device.addProtocol`) to register:

* Rogue memory or stream interface objects
* Protocol servers/clients
* Any custom object that implements ``_start()`` and/or ``_stop()``

At runtime:

* :py:meth:`~pyrogue.Device._start` calls ``_start()`` on each managed object if
  the method exists
* :py:meth:`~pyrogue.Device._stop` calls ``_stop()`` on each managed object if
  the method exists
* Both then recurse to child Devices

This is why top-level interfaces are commonly added at Root scope using
``root.addInterface(...)`` (``Root`` is a ``Device`` subclass).

Device Read/Write Operations
----------------------------

Bulk config/read/write operations traverse the tree and issue Block transactions
through Device Block APIs.

Default behavior of Block APIs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* :py:meth:`~pyrogue.Device.writeBlocks`
  initiates write transactions for this Device's Blocks (bulk-enabled Blocks by
  default), then optionally recurses into child Devices.
* :py:meth:`~pyrogue.Device.verifyBlocks`
  initiates verify transactions, then optionally recurses.
* :py:meth:`~pyrogue.Device.readBlocks`
  initiates read transactions, then optionally recurses.
* :py:meth:`~pyrogue.Device.checkBlocks`
  waits/checks completion of initiated transactions, then optionally recurses.

All four methods also support a ``variable=...`` path for targeted operations
on a specific Variable's Block instead of full-device traversal.

Parameter behavior quick reference
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Shared parameters:

* ``recurse``: include child Devices when ``True``.
* ``variable``: operate on one Variable's Block instead of full-device Block traversal.
* ``**kwargs``: forwarded to lower-level transaction helpers.

Method-specific parameters:

* ``writeBlocks(force=False, checkEach=False, index=-1, ...)``

  * ``force``: write even when values are not marked stale.
  * ``checkEach``: request per-transaction checking behavior (also affected by ``Device.forceCheckEach``).
  * ``index``: index for array-variable targeted operations.

* ``verifyBlocks(checkEach=False, ...)``

  * ``checkEach``: request per-transaction checking behavior.

* ``readBlocks(checkEach=False, index=-1, ...)``

  * ``checkEach``: request per-transaction checking behavior.
  * ``index``: index for array-variable targeted operations.

* ``checkBlocks(...)``

  * Checks completion/acknowledgement of previously initiated transactions.

Direct API references:

* :py:meth:`~pyrogue.Device.writeBlocks`
* :py:meth:`~pyrogue.Device.verifyBlocks`
* :py:meth:`~pyrogue.Device.readBlocks`
* :py:meth:`~pyrogue.Device.checkBlocks`
* :doc:`/api/python/device`

Where these methods are invoked
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These APIs are usually called by higher-level workflows rather than directly by
application code.

Single-variable access path:

* :py:meth:`~pyrogue.RemoteVariable.set` calls
  ``parent.writeBlocks(..., variable=self)`` and, depending on arguments,
  ``parent.verifyBlocks(..., variable=self)`` and
  ``parent.checkBlocks(..., variable=self)``.
* :py:meth:`~pyrogue.RemoteVariable.get` calls
  ``parent.readBlocks(..., variable=self)`` and optionally
  ``parent.checkBlocks(..., variable=self)``.

Bulk configuration/read path:

* Root ``LoadConfig`` / ``setYaml`` stage values through tree dictionary apply
  and then, when ``writeEach=False``, call Root ``_write()`` which performs:
  recursive ``writeBlocks`` -> ``verifyBlocks`` -> ``checkBlocks``.
* Root ``WriteAll`` and ``ReadAll`` commands call Root ``_write()`` and
  ``_read()``, which issue recursive all-Block operations.

This is why overriding ``writeBlocks``/``readBlocks`` at Device scope is the
normal extension point for hardware-specific sequencing behavior.

Lifecycle Hooks and Override Guidance
-------------------------------------

During :py:meth:`~pyrogue.Root.start`, Device lifecycle progresses in this order:

#. :py:meth:`~pyrogue.Device._rootAttached`
#. :py:meth:`~pyrogue.Node._finishInit` recursion
#. :py:meth:`~pyrogue.Device._start`

During :py:meth:`~pyrogue.Root.stop`, Root calls
:py:meth:`~pyrogue.Device._stop` recursively.

Guidance by hook
^^^^^^^^^^^^^^^^

* :py:meth:`~pyrogue.Device._rootAttached`

  * This is when ``self.root`` becomes valid and path/parent context is attached.
  * Default behavior also attaches children, builds Device Blocks, and applies
    ``_defaults`` overrides.
  * Use for: structural attachment-time setup that requires resolved tree context.
  * Avoid: initiating hardware transactions or starting runtime threads/services.
  * In most subclasses, do not override unless you need custom attach semantics.
    If you override, call ``super()._rootAttached(parent, root)``.

* :py:meth:`~pyrogue.Node._finishInit`

  * Runs after full attach; Variables use this stage to finalize defaults and
    poll/dependency metadata.
  * For Device subclasses, overriding is uncommon. Prefer ``__init__`` for
    static construction and ``_start()`` for runtime actions.
  * If overridden, keep it lightweight and call ``super()._finishInit()``.

* :py:meth:`~pyrogue.Device._start`

  * Runtime start hook called from Root after attach/init and worker startup.
  * Use for: starting Device-owned threads, enabling runtime subscriptions, and
    other actions that require a running system context.
  * Avoid: mutating tree structure (adding/removing Nodes or changing Block layout).
  * If overridden, preserve default managed-interface behavior by calling
    ``super()._start()`` unless you intentionally replace it.

* :py:meth:`~pyrogue.Device._stop`

  * Runtime teardown hook called during Root stop.
  * Use for: stopping threads/services and releasing runtime resources.
  * If overridden, call ``super()._stop()`` to preserve managed-interface stop.

Operational hooks and Block sequencing hooks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* Operational hooks:
  :py:meth:`~pyrogue.Device.initialize`,
  :py:meth:`~pyrogue.Device.hardReset`,
  :py:meth:`~pyrogue.Device.countReset`,
  :py:meth:`~pyrogue.Device.enableChanged`
* Block sequencing hooks:
  :py:meth:`~pyrogue.Device.writeBlocks`,
  :py:meth:`~pyrogue.Device.verifyBlocks`,
  :py:meth:`~pyrogue.Device.readBlocks`,
  :py:meth:`~pyrogue.Device.checkBlocks`

``initialize``/``hardReset``/``countReset`` are invoked by Root-level command
workflows, not automatically by ``Root.start()``/``Root.stop()``.

Practical note on variable access timing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``self.root`` is not valid before ``_rootAttached``.
* RemoteVariable Block mapping is finalized during ``_rootAttached``.
* Variable shadow values can be set before start (for example with ``write=False``),
  but hardware-backed reads/writes should be treated as runtime operations and
  performed after Root has started.

Example: prefer ``_start()``/``_stop()`` for runtime work
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
               # Runtime activity here
               time.sleep(0.1)

Custom Read/Write Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Override Block APIs when hardware requires extra ordering that is not captured
by standard Block traversal alone.

Common reasons to override:

* One register must be written before or after bulk config writes
* Paged/banked register windows need explicit page-select writes around access
* A side-effect register must be pulsed to commit staged settings
* Custom sequencing across child Devices is required

If a Device needs custom sequencing around default Block operations, override:

* :py:meth:`~pyrogue.Device.writeBlocks`
* :py:meth:`~pyrogue.Device.verifyBlocks`
* :py:meth:`~pyrogue.Device.readBlocks`
* :py:meth:`~pyrogue.Device.checkBlocks`

General override pattern
""""""""""""""""""""""""

Keep default traversal unless you explicitly want to replace it:

* Call ``super()`` for standard Block behavior
* Preserve key arguments (``recurse``, ``variable``, ``checkEach``, ``**kwargs``)
* Add only the extra hardware-specific step(s)

Example: activation register after config writes
""""""""""""""""""""""""""""""""""""""""""""""""

Some ASICs require an explicit apply/activate write after normal register
configuration is sent.

.. code-block:: python

   import pyrogue as pr

   class AsicDevice(pr.Device):
       def writeBlocks(self, *, force=False, recurse=True, variable=None, checkEach=False, index=-1, **kwargs):
           # Normal write traversal first.
           super().writeBlocks(
               force=force,
               recurse=recurse,
               variable=variable,
               checkEach=checkEach,
               index=index,
               **kwargs,
           )

           # Only run activation for full-device writes.
           if variable is None:
               # Commit/apply staged config in ASIC.
               self.Activate.set(1, write=True, verify=False, check=True)

Example: page-select around reads
"""""""""""""""""""""""""""""""""

.. code-block:: python

   import pyrogue as pr

   class PagedDevice(pr.Device):
       def readBlocks(self, *, recurse=True, variable=None, checkEach=False, index=-1, **kwargs):
           if variable is None:
               # Select status page before bulk read.
               self.PageSel.set(2, write=True, verify=False, check=True)

           super().readBlocks(
               recurse=recurse,
               variable=variable,
               checkEach=checkEach,
               index=index,
               **kwargs,
           )

Implementation Boundary (Python and C++)
----------------------------------------

From a Python API perspective, you use ``pyrogue.Device`` methods such as
``readBlocks`` and ``writeBlocks``.

Under the hood, ``pyrogue.Device`` is built on the Rogue memory interface
Hub/Master/Slave stack. In particular, a Device participates in memory routing
as a Hub, and forwards block transactions toward downstream memory slaves.

Where Hub fits in transaction flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The C++ Hub implementation (``src/rogue/interfaces/memory/Hub.cpp``):

* Applies local address offset when forwarding transactions downstream
* Can split large transactions into sub-transactions based on downstream
  max-access limits
* Allows custom transaction translation by overriding ``_doTransaction`` in
  Python/C++ subclasses

Conceptual transaction path:

* Variable operation -> Block transaction -> Device/Hub routing ->
  downstream slave access -> completion/check -> Variable update notify

For deeper memory-stack behavior, see:

* :doc:`/pyrogue_tree/core/block`
* :doc:`/memory_interface/hub`
* :doc:`/memory_interface/slave`
* :doc:`/api/cpp/interfaces/memory/index`


Device Command Decorators
-------------------------

Device supports decorators that create :py:class:`~pyrogue.LocalCommand` Nodes.
You can use decorators on local functions created in ``__init__``.

.. code-block:: python

   @pyrogue.command(name='ReadConfig', value='', description='Load config file')
   def _readConfig(self, arg):
       self.root.loadYaml(name=arg, writeEach=False, modes=['RW', 'WO'])

Special Device Subclasses
=========================

PyRogue provides several built-in ``Device`` subclasses for common workflows.
These are documented in the dedicated built-in section:

* :doc:`/pyrogue_tree/builtin_devices/index`

Frequently used examples include:

* :doc:`/pyrogue_tree/builtin_devices/run_control`
* :doc:`/pyrogue_tree/builtin_devices/data_writer`
* :doc:`/pyrogue_tree/builtin_devices/data_receiver`
* :doc:`/pyrogue_tree/builtin_devices/prbspair`

API Reference
=============

See :doc:`/api/python/device` for generated API details.
