.. _protocols_gpib:

=============
GPIB Protocol
=============

The GPIB-based instrument interface is implemented in
``python/pyrogue/protocols/gpib.py``.

Rogue models GPIB instruments as a memory-style control path so normal
``RemoteVariable`` access can drive SCPI-style commands. This is useful for lab
equipment that already has a stable command set but does not present a register
bus in the FPGA sense.

Overview
========

The implementation has two layers:

- ``GpibController``:
  A memory ``Slave`` that translates transactions into GPIB read/write
  operations
- ``GpibDevice``:
  A ``pyrogue.Device`` wrapper that owns the controller and registers Variables
  with it

Each mapped Variable must provide a ``key`` extra attribute. That key is used
as the SCPI command prefix.

Transaction model
=================

The controller translates memory transactions as follows:

- Write:
  decode the transaction bytes using the Variable Model, then send
  ``<key> <display_value>``
- Read or Verify:
  send ``<key>?``, read back the instrument response string, parse it through
  the Variable display/parser path, then return the encoded bytes to the
  transaction
- Post:
  not currently supported

This means the Variable's Model and display/parsing behavior are part of the
protocol contract, not just the tree presentation.

Dependencies
============

This interface depends on the external ``gpib_ctypes`` package and a working
GPIB stack on the host:

.. code-block:: bash

   pip install gpib_ctypes

The module source also references additional host setup guidance at:

https://gist.github.com/ochococo/8362414fff28fa593bc8f368ba94d46a

Defining Variables
==================

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

How the wrapper works
=====================

``GpibDevice`` creates a ``GpibController`` and installs it as ``memBase``.
When you add a Variable that includes ``extraArgs={'key': ...}``, the wrapper
registers that Variable with the controller so transactions at the Variable
offset can be translated into GPIB commands.

This keeps the user-facing PyRogue model conventional even though the
underlying instrument interface is command-oriented.

Code-backed example
===================

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

Operational notes
=================

- The transaction size must match the Variable's encoded byte width.
- Readback parsing depends on the instrument returning a string compatible with
  the Variable's display parser.
- Posted writes are not supported.
- This path is appropriate for low-rate instrument control and monitoring, not
  high-rate acquisition.

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

This logger is useful for command/response tracing because it emits messages
such as:

- ``Write Sending <command>``
- ``Read Sending <command?>``
- ``Read Got: <response>``

Related Topics
==============

- PyRogue Variable behavior: :doc:`/pyrogue_tree/core/variable`
- Model conversion rules: :doc:`/pyrogue_tree/core/model`
- Memory-style transaction flow: :doc:`/memory_interface/index`
