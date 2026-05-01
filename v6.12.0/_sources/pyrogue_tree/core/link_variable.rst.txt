.. _pyrogue_tree_node_variable_link_variable:

============
LinkVariable
============

:py:class:`~pyrogue.LinkVariable` exposes a derived value backed by one or more
dependency Variables. It is useful for unit conversion, bit-field composition,
and user-friendly computed views.

The most common application use case is converting raw ADC or DAC register
values into real engineering units while still preserving direct access to the
underlying raw Variables.

When To Use LinkVariable
========================

Use ``LinkVariable`` when the important user-facing value is derived from one
or more other Variables rather than owned directly by software or mapped
directly to hardware.

That makes it the presentation-oriented counterpart to the other Variable
types:

* ``LocalVariable`` owns software state
* ``RemoteVariable`` maps hardware state
* ``LinkVariable`` computes or transforms a value from dependencies

This is often the best way to expose engineering units, calibrated views,
composite bit fields, or operator-friendly abstractions without hiding the raw
registers that developers may still need.

What You Usually Set
====================

Most ``LinkVariable`` definitions use the shared Variable parameters from
:doc:`/pyrogue_tree/core/variable`, plus the linked-logic parameters that make
the node derived rather than directly stored:

* ``dependencies`` for the source Variables.
* ``linkedGet`` for read-side conversion.
* ``linkedSet`` for write-side conversion.

Some code also uses the ``variable=...`` shortcut to mirror another Variable
directly and then override only selected presentation properties or callback
behavior.

When you pass ``variable=some_var``, PyRogue automatically uses that
Variable's ``get()`` and ``set()`` methods as the linked access behavior and
adds it as a dependency. In other words, this is the quick way to build a
single-source ``LinkVariable`` without spelling out both ``dependencies`` and
the default callbacks yourself.

This is most useful when you want a second view of one Variable that differs
mainly in presentation, naming, grouping, or a small override to the default
linked behavior.

Callbacks And Dependencies
==========================

``LinkVariable`` typically uses:

* ``dependencies``: source Variables used by linked logic
* ``linkedGet``: compute displayed value from dependencies
* ``linkedSet``: convert user value back to dependency writes

In the current implementation, the callback wrappers support keyword arguments
matching:

* ``linkedGet(dev=None, var=None, read=True, index=-1, check=True)``
* ``linkedSet(dev=None, var=None, value=..., write=True, index=-1, verify=True, check=True)``

The callback may accept any subset of those parameters. This gives the linked logic
access to the surrounding ``Device``, the ``LinkVariable`` itself, and the
normal read/write control flags when needed.

The ``read`` and ``write`` controls are especially important:

* ``read`` tells ``linkedGet`` whether the caller wants fresh data from the
  dependencies or only the currently cached values.
* ``write`` tells ``linkedSet`` whether dependency updates should actually be
  committed or only staged locally.

That means a good ``LinkVariable`` implementation usually preserves the
caller's intent. If a caller requests ``get(read=False)``, the linked logic
should usually avoid forcing extra hardware reads. If a caller requests
``set(write=False)``, the linked logic should usually avoid committing the
dependency writes immediately.

This is one of the most important design points for ``LinkVariable`` callbacks:
they should usually forward ``read`` and ``write`` into dependency accesses
rather than hard-code ``read=True`` or ``write=True``.

LinkVariable Chaining
=====================

``LinkVariable`` dependencies can include other ``LinkVariable`` instances, so
you can build layered conversions (for example raw ADC counts -> volts ->
engineering quantity such as power, temperature, or calibrated sensor units).

This is useful when:

* One conversion step is reused by multiple higher-level views
* You want to separate low-level scaling from calibration or application logic
* Derived values should remain readable and testable as independent Nodes

Design Guidance
===============

Good ``LinkVariable`` usage usually follows a simple rule: keep the raw
Variables visible, and use ``LinkVariable`` to add a clearer operational view
rather than to hide the hardware interface entirely.

In practice:

* Use ``RemoteVariable`` for the raw register surface
* Add one or more ``LinkVariable`` Nodes for engineering units or derived views
* Keep the conversion logic small, readable, and easy to test
* Prefer helper functions over dense lambdas once the math or policy becomes
  non-trivial
* Preserve caller intent by forwarding ``read`` and ``write`` into dependency
  accesses unless the linked behavior intentionally overrides that policy
* Consider subclassing ``LinkVariable`` when the same linked-access pattern is
  reused across many nodes

Examples
========

Mirroring A Single Variable With ``variable=``
----------------------------------------------

The ``variable=...`` shortcut is useful when you want a second tree-facing
view of one Variable without writing explicit ``dependencies``,
``linkedGet``, and ``linkedSet`` boilerplate.

.. code-block:: python

   import pyrogue as pr

   class PowerMonitor(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='VoltageRaw',
               offset=0x00,
               bitSize=16,
               mode='RO',
               base=pr.UInt,
               hidden=True,
           ))

           self.add(pr.LinkVariable(
               name='VoltageCounts',
               variable=self.VoltageRaw,
               mode='RO',
               disp='{:#06x}',
               description='Mirror of VoltageRaw with operator-facing formatting',
           ))

In this pattern, ``VoltageCounts`` reuses ``VoltageRaw`` for storage and read
behavior, but presents it as a separate node with its own name, description,
and formatting. This is a good fit when you want an alternate tree-facing view
without introducing any new conversion logic.

Engineering-Unit View Of A Raw Register
---------------------------------------

One common pattern is to pair a hidden raw ``RemoteVariable`` with a
user-facing ``LinkVariable`` that converts the raw count into engineering
units.

.. code-block:: python

   import pyrogue as pr

   class TempMonitor(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='TempRaw',
               offset=0x100,
               bitSize=12,
               mode='RO',
               base=pr.UInt,
           ))
           

           self.add(pr.LinkVariable(
               name='Temperature',
               units='degC',
               mode='RO',
               dependencies=[self.TempRaw], # add()ed Nodes can be accessed as attributes
               linkedGet=lambda var, read=True: (var.dependencies[0].get(read=read) * 0.1) - 40.0,
           ))

The important detail is that ``linkedGet`` forwards the caller's ``read``
choice to the dependency. That preserves the normal Variable behavior: callers
can choose between a fresh read and the currently cached value.

Composite Value Built From Multiple Register Fields
---------------------------------------------------

Another common pattern is assembling one logical value from several underlying
register fields.

.. code-block:: python

   import pyrogue as pr

   class MyAdc(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(name='MaskLow',  offset=0x10, bitSize=4, mode='RW'))
           self.add(pr.RemoteVariable(name='MaskHigh', offset=0x14, bitSize=4, mode='RW'))
           self.add(pr.RemoteVariable(name='MaskDf',   offset=0x14, bitSize=2, bitOffset=4, mode='RW'))

           def _get_mask(var, read=True):
               low  = var.dependencies[0].get(read=read)
               high = var.dependencies[1].get(read=read)
               df   = var.dependencies[2].get(read=read)
               return (df << 8) | (high << 4) | low

           def _set_mask(var, value, write=True):
               var.dependencies[0].set(value & 0xF, write=False)
               var.dependencies[1].set((value >> 4) & 0xF, write=False)
               var.dependencies[2].set((value >> 8) & 0x3, write=False)
               if write:
                   var.parent.writeBlocks()

           self.add(pr.LinkVariable(
               name='DeviceMask',
               disp='{:#b}',
               dependencies=[self.MaskLow, self.MaskHigh, self.MaskDf],
               linkedGet=_get_mask,
               linkedSet=_set_mask,
           ))

This pattern is useful when the hardware register map is fragmented but the
user-facing control should look like one coherent value.

ADC Counts to Input Voltage (Read-Only)
---------------------------------------

.. code-block:: python

   import pyrogue as pr

   class AdcMonitor(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='AdcRaw',
               offset=0x200,
               bitSize=16,
               mode='RO',
               base=pr.UInt,
           ))

           # 16-bit ADC, 2.5 V full-scale, no offset
           self.add(pr.LinkVariable(
               name='InputVoltage',
               units='V',
               mode='RO',
               disp='{:.6f}',
               dependencies=[self.AdcRaw],
               linkedGet=lambda var, read=True: (
                   var.dependencies[0].get(read=read) * (2.5 / 65535.0)
               ),
           ))

DAC Voltage Setpoint to Raw Code (Read/Write)
----------------------------------------------

.. code-block:: python

   import pyrogue as pr

   class DacControl(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='DacRaw',
               offset=0x300,
               bitSize=14,
               mode='RW',
               base=pr.UInt,
           ))

           full_scale = 1.8
           max_code = (1 << 14) - 1

           self.add(pr.LinkVariable(
               name='DacSetpoint',
               units='V',
               mode='RW',
               disp='{:.5f}',
               dependencies=[self.DacRaw],
               linkedGet=lambda var, read=True: (
                   var.dependencies[0].get(read=read) * (full_scale / max_code)
               ),
               linkedSet=lambda var, value, write=True: (
                   var.dependencies[0].set(
                       max(0, min(max_code, int(round((float(value) / full_scale) * max_code)))),
                       write=write,
                   )
               ),
           ))

ADC Conversion with Multiple Dependencies (Read-Only)
-----------------------------------------------------

.. code-block:: python

   import pyrogue as pr

   class AdcWithGain(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='AdcRaw',
               offset=0x400,
               bitSize=16,
               mode='RO',
               base=pr.UInt,
           ))

           self.add(pr.RemoteVariable(
               name='GainRaw',
               offset=0x404,
               bitSize=4,
               mode='RO',
               base=pr.UInt,
           ))

           def _scaled_input(var, read=True):
               adc_raw = var.dependencies[0].get(read=read)
               gain_raw = var.dependencies[1].get(read=read)
               adc_volts = adc_raw * (2.5 / 65535.0)
               gain = 1 << gain_raw  # 0->1x, 1->2x, 2->4x, ...
               return adc_volts / gain

           self.add(pr.LinkVariable(
               name='InputVoltageScaled',
               mode='RO',
               units='V',
               disp='{:.6f}',
               dependencies=[self.AdcRaw, self.GainRaw],
               linkedGet=_scaled_input,
           ))

Subclassing LinkVariable
------------------------

An occasional pattern is to subclass ``LinkVariable`` when the same
linked-access behavior needs to be reused many times. This is useful when the
linked logic is more like a reusable Variable type than a one-off callback.

Two common examples are:

* An indexed view into one element of an array-like dependency
* A grouped Variable that reads or writes a coordinated set of dependencies

.. code-block:: python

   import pyrogue as pr

   class IndexedLinkVariable(pr.LinkVariable):
       def __init__(self, dep, index, **kwargs):
           super().__init__(linkedGet=self._get, linkedSet=self._set, **kwargs)
           self.dep = dep
           self.index = index

       def _get(self, *, read):
           return self.dep.get(read=read, index=self.index)

       def _set(self, *, value, write):
           self.dep.set(value=value, index=self.index, write=write)

This pattern is a good fit when many nodes should expose the same linked
behavior with different dependencies or indices. It keeps the tree definition
cleaner and avoids large repeated lambdas.

What To Explore Next
====================

* Software-owned Variables: :doc:`/pyrogue_tree/core/local_variable`
* Hardware-backed Variables: :doc:`/pyrogue_tree/core/remote_variable`
* Shared Variable behavior: :doc:`/pyrogue_tree/core/variable`

API Reference
=============

See :doc:`/api/python/pyrogue/linkvariable` for generated API details.
