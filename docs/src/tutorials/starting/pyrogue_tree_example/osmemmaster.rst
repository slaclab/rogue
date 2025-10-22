.. _interfaces_python_osmemmaster:

======================================
Python OsMemMaster Class Documentation
======================================

OsMemMaster 

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