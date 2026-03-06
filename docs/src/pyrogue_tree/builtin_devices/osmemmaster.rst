.. _interfaces_python_osmemmaster:

==========================
OsMemMaster Device Example
==========================

``OsMemMaster`` is an example ``Device`` that exposes host OS metrics as
``RemoteVariable`` entries through a memory-backed path.

It demonstrates how to map non-hardware data sources into the normal PyRogue
tree model so they can be read, monitored, and grouped like other Variables.

The implementation lives in ``python/pyrogue/examples/_OsMemMaster.py``.

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

Related APIs:

- :doc:`/api/python/device`
- :doc:`/api/python/remotevariable`
