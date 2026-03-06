.. _pyrogue_tree_node_variable_link_variable:

============
LinkVariable
============

:py:class:`~pyrogue.LinkVariable` exposes a derived value backed by one or more
dependency Variables. It is useful for unit conversion, bit-field composition,
and user-friendly computed views.

The most common application use case is converting raw ADC/DAC register values
into real engineering units (for example volts, amps, degC, dBm) while still
keeping direct access to the underlying raw registers.

Behavior
========

``LinkVariable`` typically uses:

* ``dependencies``: source Variables used by linked logic
* ``linkedGet``: compute displayed value from dependencies
* ``linkedSet``: convert user value back to dependency writes

LinkVariable Chaining
=====================

``LinkVariable`` dependencies can include other ``LinkVariable`` instances, so
you can build layered conversions (for example raw ADC counts -> volts ->
engineering quantity such as power, temperature, or calibrated sensor units).

This is useful when:

* one conversion step is reused by multiple higher-level views
* you want to separate low-level scaling from calibration/application logic
* derived values should remain readable and testable as independent Nodes

Examples
========

ADC Counts to Temperature
-------------------------

.. code-block:: python

   import pyrogue as pr

   class MyDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           self.add(pr.RemoteVariable(
               name='TempRaw',
               offset=0x100,
               bitSize=12,
               mode='RW',
               base=pr.UInt,
           ))
           

           self.add(pr.LinkVariable(
               name='Temperature',
               units='degC',
               mode='RW',
               dependencies=[self.TempRaw], # add()ed Nodes can be accessed as attributes
               linkedGet=lambda var, read=True: (var.dependencies[0].get(read=read) * 0.1) - 40.0,
               linkedSet=lambda var, value, write=True: var.dependencies[0].set(int((value + 40.0) / 0.1), write=write),
           ))

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

LinkVariable API Reference
================================

See :doc:`/api/python/linkvariable` for generated API details.
