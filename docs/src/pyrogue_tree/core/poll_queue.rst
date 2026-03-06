.. _pyrogue_tree_root_poll_queue:

=========
PollQueue
=========

:py:class:`pyrogue.PollQueue` is the Root-owned scheduler that drives periodic
reads for polled variables.

In most applications you do not instantiate it directly. It is created by
:py:class:`pyrogue.Root` and controlled through root-level APIs/variables such
as ``PollEn`` and variable ``pollInterval``.

Polling strategy
================

- Poll only values that change over time and are operationally important.
- Keep fast and slow update classes on separate poll intervals where possible.
- Avoid aggressive polling on high-latency links unless required.

Common pattern
==============

1. Assign poll intervals by value volatility and operator need.
2. Validate update rate under realistic network and load conditions.
3. Move exceptions to event-driven paths or explicit command reads when needed.

What it does
============

At runtime, PollQueue:

* tracks poll entries per memory block (not per variable)
* schedules reads using a time-ordered heap
* issues block read transactions with ``startTransaction(..., Read)``
* waits for completion via ``checkTransaction``
* wraps each poll batch in ``root.updateGroup()`` so updates are coalesced

Block-Level Scheduling Behavior
===============================

Polling is organized per block:

* if multiple variables share a block, the block is polled at the minimum
  non-zero ``pollInterval`` among those variables
* when intervals change, the corresponding block entry is updated/replaced
* if no variables in a block have ``pollInterval > 0``, that block is removed
  from the poll queue

Special case for variables without a hardware block:

* for dependency-only variables (for example link variables without ``_block``),
  interval updates are propagated to dependencies

Control and Lifecycle
=====================

* Poll thread starts during :py:meth:`pyrogue.Root.start`.
* ``Root.PollEn`` controls pause/unpause (enabled when ``True``).
* Poll thread exits during :py:meth:`pyrogue.Root.stop`.
* :py:meth:`pyrogue.Root.pollBlock` can temporarily block polling inside a
  context manager.

Usage Examples
==============

Basic polling on a RemoteVariable
---------------------------------

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add(pr.RemoteVariable(
               name='AdcRaw',
               offset=0x100,
               bitSize=16,
               mode='RO',
               base=pr.UInt,
               pollInterval=1.0,  # poll every second
           ))

Runtime control from Root
-------------------------

.. code-block:: python

   # Enable/disable polling globally
   root.PollEn.set(True)
   root.PollEn.set(False)

   # Change polling rate dynamically for one variable
   root.MyDevice.AdcRaw.setPollInterval(0.2)

Temporarily block polling during a critical sequence
----------------------------------------------------

.. code-block:: python

   with root.pollBlock():
       # perform operations that should not race with background poll reads
       root.MyDevice.SomeControl.set(1)
       root.MyDevice.OtherControl.set(0)

PollQueue API Reference
=============================

See :doc:`/api/python/pollqueue` for generated API details.
