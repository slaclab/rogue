.. _pyrogue_tree_root_poll_queue:

=========
PollQueue
=========

:py:class:`~pyrogue.PollQueue` is the Root-owned scheduler that drives periodic
reads for polled Variables.

In most applications you do not instantiate it directly. It is created by
:py:class:`~pyrogue.Root` and controlled through Root-level APIs/Variables such
as ``PollEn`` and Variable ``pollInterval``.

Polling is one of the places where the PyRogue tree stops being a static object
model and becomes a live system. Once enabled, the poll queue continually
issues background reads for the Variables that asked for them.

Polling Strategy
================

Use polling for status that genuinely changes over time and that operators or
software need to see without an explicit read.

In practice:

* Poll telemetry, counters, and dynamic status.
* Keep fast and slow update classes on separate poll intervals where possible.
* Avoid aggressive polling on high-latency or low-bandwidth links unless the
  application really needs it.

What It Does
============

At runtime, PollQueue:

* Tracks poll entries per Block (not per Variable)
* Schedules reads using a time-ordered heap
* Issues Block read transactions with ``startTransaction(..., Read)``
* Waits for completion via ``checkTransaction``
* Wraps each poll batch in ``root.updateGroup()`` so updates are coalesced

The block-level design is important. PollQueue does not schedule one hardware
transaction per Variable. It schedules one transaction per ``Block``, because
that is the real memory transaction unit underneath the Variable API.

Block-Level Scheduling
======================

Polling is organized per Block:

* If multiple Variables share a Block, the Block is polled at the minimum
  non-zero ``pollInterval`` among those Variables
* When intervals change, the corresponding Block entry is updated/replaced
* If no Variables in a Block have ``pollInterval > 0``, that Block is removed
  from the poll queue

That behavior preserves the efficiency benefit of Block grouping. Two Variables
in the same register word do not create two independent background reads.

There is one special case for Variables without a hardware Block:

* For dependency-only Variables (for example LinkVariables without ``_block``),
  interval updates are propagated to dependencies

The implementation also schedules new poll entries for immediate service when
polling is enabled. In practice, a newly polled Variable usually gets its
first background read right away rather than waiting for one full interval.

Control and Lifecycle
=====================

* The poll thread is created by ``Root`` and starts during :py:meth:`~pyrogue.Root.start`.
* Poll activity begins paused; ``Root.PollEn`` enables or disables active polling.
* Poll thread exits during :py:meth:`~pyrogue.Root.stop`.
* :py:meth:`~pyrogue.Root.pollBlock` can temporarily block polling inside a
  context manager.

``pollBlock()`` is the important synchronization tool when a short software
sequence should not race with background reads. Internally, PollQueue tracks a
block counter and waits until those critical sections are released before
issuing the next poll batch.

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

   # Change polling rate dynamically for one Variable
   root.MyDevice.AdcRaw.setPollInterval(0.2)

Temporarily block polling during a critical sequence
----------------------------------------------------

.. code-block:: python

   with root.pollBlock():
       # perform operations that should not race with background poll reads
       root.MyDevice.SomeControl.set(1)
       root.MyDevice.OtherControl.set(0)

What To Explore Next
====================

* Variable polling configuration: :doc:`/pyrogue_tree/core/variable`
* Root lifecycle and background services: :doc:`/pyrogue_tree/core/root`
* Block transaction grouping: :doc:`/pyrogue_tree/core/block`

API Reference
=============

See :doc:`/api/python/pyrogue/pollqueue` for generated API details.
