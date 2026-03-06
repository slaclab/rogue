.. _interfaces_python_osmemmaster:

==========================
OsMemMaster Device Example
==========================

``OsMemMaster`` is an example ``Device`` that exposes host OS metrics as
``RemoteVariable`` entries through a memory-backed path.

It demonstrates how to map non-hardware data sources into the normal PyRogue
tree model so they can be read, monitored, and grouped like other Variables.

The implementation lives in ``python/pyrogue/examples/_OsMemMaster.py``.

Why This Example Is Useful
==========================

``OsMemMaster`` shows how a normal PyRogue ``Device`` can read/write against a
non-hardware backend when a compatible memory ``Slave`` is provided. In the
example flow:

- ``OsMemMaster`` defines typed ``RemoteVariable`` objects at fixed offsets.
- ``OsMemSlave`` (a subclass of
  :py:class:`~pyrogue.interfaces.OsCommandMemorySlave`) implements those same
  offsets with Python callables.
- Variable reads/writes from the tree become memory transactions to the slave,
  which executes host-side logic and returns data.

Example Wiring In A Root
========================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.examples as pre

   class ExampleRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           os_slave = pre.OsMemSlave()
           os_slave.setName('OsSlave')
           self.addInterface(os_slave)

           # Device uses the slave as memBase.
           self.add(pre.OsMemMaster(memBase=os_slave))

In this setup:

- ``Uptime`` and ``SysLoad*`` variables read host metrics.
- ``FileTest`` demonstrates a read/write path through the same interface.

.. code-block:: python

    class OsMemMaster(pr.Device):

        # Last comment added by rherbst for demonstration.
        def __init__(
                self,
                name             = 'OsMemMaster',
                description      = 'OS Memory Master Device',
                **kwargs):

            pr.Device.__init__(
                self,
                name        = name,
                description = description,
                **kwargs)

            ##############################
            # Variables
            ##############################

            self.add(pr.RemoteVariable(
                name         = 'Uptime',
                description  = 'System Uptime In Seconds',
                offset       = 0x00,
                bitSize      = 32,
                base         = pr.Float,
                mode         = 'RO',
                pollInterval = 1
            ))

            self.add(pr.RemoteVariable(
                name         = 'SysLoad1Min',
                description  = '1 Minute System Load',
                offset       = 0x04,
                bitSize      = 32,
                base         = pr.Float,
                mode         = 'RO',
                pollInterval = 1
            ))

            self.add(pr.RemoteVariable(
                name         = 'SysLoad5Min',
                description  = '5 Minute System Load',
                offset       = 0x08,
                bitSize      = 32,
                base         = pr.Float,
                mode         = 'RO',
                pollInterval = 1
            ))

            self.add(pr.RemoteVariable(
                name         = 'SysLoad15Min',
                description  = '15 Minute System Load',
                offset       = 0x0C,
                bitSize      = 32,
                base         = pr.Float,
                mode         = 'RO',
                pollInterval = 1
            ))

            self.add(pr.RemoteVariable(
                name         = 'FileTest',
                description  = 'File Read Write Test',
                offset       = 0x10,
                bitSize      = 32,
                base         = pr.UInt,
                mode         = 'RW',
            ))

Operational Notes
=================

- Poll intervals on RO variables drive periodic reads through ``memBase``.
- Address offsets and ``base`` Model types must match the slave command map.
- This pattern is for integration and prototyping, not low-latency data paths.

Related APIs
============

- :doc:`/api/python/device`
- :doc:`/api/python/remotevariable`
- :doc:`/built_in_modules/os_memory_bridge/os_command_memory_slave`
