.. _protocols_gpib:

============
GPIB Control
============

For instrument control over a host GPIB stack, PyRogue provides
``pyrogue.protocols.gpib`` so SCPI-style commands can be exposed through the
normal ``RemoteVariable`` memory-access model. This is the right fit when a lab
instrument already has a stable command set but does not present a register bus
in the FPGA sense.

The implementation has two layers. ``GpibController`` is a memory ``Slave``
that translates transactions into GPIB read and write operations, and
``GpibDevice`` is the ``pyrogue.Device`` wrapper that owns that controller and
registers Variables with it. Each mapped Variable must provide a ``key`` extra
attribute, because that key becomes the SCPI command prefix used on the wire.

Host Dependencies
=================

This interface depends on the external ``gpib_ctypes`` package and a working
GPIB stack on the host:

.. code-block:: bash

   pip install gpib_ctypes

The module source also references additional host setup guidance at:

https://gist.github.com/ochococo/8362414fff28fa593bc8f368ba94d46a

GpibDevice Workflow
===================

``GpibDevice`` keeps the user-facing PyRogue model conventional even though the
underlying instrument interface is command-oriented:

- It creates a ``GpibController`` and installs it as ``memBase``.
- It registers Variables that carry ``extraArgs={'key': ...}``.
- Reads and verifies send ``<key>?``, parse the response with the Variable
  display/parser path, and return the encoded bytes to the transaction.
- Writes decode the transaction bytes with the Variable Model and send
  ``<key> <display_value>``.
- Posted writes are not currently supported.

Configuration Example
=====================

Variables should be created with a ``key`` extra attribute matching the
instrument command name.

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols.gpib as pgp

   class MyInstrument(pgp.GpibDevice):
       def __init__(self, **kwargs):
           super().__init__(gpibAddr=5, gpibBoard=0, **kwargs)

           self.add(pr.RemoteVariable(
               name='Voltage',
               description='Output voltage setpoint/readback',
               offset=0x00,
               bitSize=32,
               base=pr.Float,
               mode='RW',
               extraArgs={'key': 'VOLT'},
           ))

           self.add(pr.RemoteVariable(
               name='Current',
               description='Output current setpoint/readback',
               offset=0x04,
               bitSize=32,
               base=pr.Float,
               mode='RW',
               extraArgs={'key': 'CURR'},
           ))

Key Constructor Arguments
=========================

- ``gpibAddr`` selects the instrument address on the bus.
- ``gpibBoard`` selects the host GPIB board number when more than one board is
  present.
- ``timeout`` controls how long the GPIB layer waits for command completion.

For Variables, the most important configuration point is the ``key`` extra
attribute, because the controller uses that key to build the SCPI command
string. The Variable Model and display/parser behavior are therefore part of
the protocol contract, not just tree presentation.

Instrument Example
==================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols.gpib as pgp

   class PowerSupply(pgp.GpibDevice):
       def __init__(self, **kwargs):
           super().__init__(
               name='PowerSupply',
               description='Example SCPI instrument on GPIB',
               gpibAddr=5,
               gpibBoard=0,
               **kwargs,
           )

           # Writes send "VOLT <value>", reads send "VOLT?"
           self.add(pr.RemoteVariable(
               name='Voltage',
               offset=0x00,
               bitSize=32,
               base=pr.Float,
               mode='RW',
               extraArgs={'key': 'VOLT'},
           ))

           # Writes send "OUTP <value>", reads send "OUTP?"
           self.add(pr.RemoteVariable(
               name='OutputEnable',
               offset=0x04,
               bitSize=1,
               base=pr.Bool,
               mode='RW',
               extraArgs={'key': 'OUTP'},
           ))

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot')
           self.add(PowerSupply())

Operational Notes
=================

The transaction size must match the Variable's encoded byte width, because the
controller checks the byte count before issuing the GPIB command. Readback
parsing depends on the instrument returning a string compatible with the
Variable's display parser. This path is intended for low-rate instrument
control and monitoring, not for high-rate acquisition.

Logging
=======

``GpibController`` uses Python logging.

The logger name includes the board and address:

- Pattern: ``pyrogue.GpibController.GPIB.<board>.<addr>``
- Example: ``pyrogue.GpibController.GPIB.0.5``

Configuration example:

.. code-block:: python

   import logging

   logging.getLogger('pyrogue.GpibController').setLevel(logging.DEBUG)

This logger is useful for command and response tracing because it emits
messages such as:

- ``Write Sending <command>``
- ``Read Sending <command?>``
- ``Read Got: <response>``

Related Topics
==============

- PyRogue Variable behavior: :doc:`/pyrogue_tree/core/variable`
- Model conversion rules: :doc:`/pyrogue_tree/core/model`
- Memory-style transaction flow: :doc:`/memory_interface/index`

API Reference
=============

- Python:

  - :doc:`/api/python/pyrogue/protocols/gpibcontroller`
  - :doc:`/api/python/pyrogue/protocols/gpibdevice`
