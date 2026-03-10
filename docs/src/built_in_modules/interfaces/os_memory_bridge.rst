.. _built_in_modules_os_memory_bridge:
.. _interfaces_python_os_command_memory_slave:
.. _interfaces_python_osmemmaster:

================
OS Memory Bridge
================

The OS memory bridge pattern maps memory transactions to host-side Python
functions so standard ``RemoteVariable`` access can target non-hardware data
sources.

The bridge is typically built from two parts used together:

- :py:class:`~pyrogue.interfaces.OsCommandMemorySlave`: a memory ``Slave`` that
  maps addresses to Python command callbacks.
- ``OsMemMaster``: an example ``Device`` that exposes ``RemoteVariable`` Nodes
  at those same offsets.

This pairing is useful for prototyping register maps, exposing host metrics
inside a tree, and testing memory-control paths before firmware is available.

OsCommandMemorySlave
====================

:py:class:`~pyrogue.interfaces.OsCommandMemorySlave` maps read/write
transactions to Python callables keyed by address.

How mapping works:

- Write/Post transaction: bytes are decoded with the registered ``base`` Model
  and passed to the callback as ``arg``.
- Read transaction: callback is invoked with ``arg=None``; return value is
  encoded with the same Model and returned as transaction data.

Commands are registered with ``@self.command(addr=..., base=...)``.

Method and Mapping Overview
---------------------------

- ``@self.command(addr=..., base=...)`` registers one address callback.
- ``addr`` defines the transaction-mapped register offset.
- ``base`` defines encode/decode model for read/write payload conversion.
- Callback ``arg`` behavior:
  - ``arg is None`` on read transactions.
  - ``arg`` contains decoded write value on write/post transactions.

.. code-block:: python

   import os
   import pathlib
   import time
   import pyrogue as pr
   import pyrogue.interfaces as pri

   class MyCmdSlave(pri.OsCommandMemorySlave):
       def __init__(self):
           super().__init__(minWidth=4, maxSize=256)

           @self.command(addr=0x00, base=pr.Float(32))
           def Uptime(self, arg):
               # Read-only command: ignore writes.
               if arg is None:
                   return float(time.monotonic())
               return float(time.monotonic())

           @self.command(addr=0x04, base=pr.Float(32))
           def SysLoad1Min(self, arg):
               if arg is None:
                   return float(os.getloadavg()[0])
               return float(os.getloadavg()[0])

           @self.command(addr=0x08, base=pr.Float(32))
           def SysLoad5Min(self, arg):
               if arg is None:
                   return float(os.getloadavg()[1])
               return float(os.getloadavg()[1])

           @self.command(addr=0x0C, base=pr.Float(32))
           def SysLoad15Min(self, arg):
               if arg is None:
                   return float(os.getloadavg()[2])
               return float(os.getloadavg()[2])

           @self.command(addr=0x10, base=pr.UInt(32))
           def FileTest(self, arg):
               # RW path matching OsMemMaster.FileTest.
               if arg is not None:
                   pathlib.Path('/tmp/osCmdTest.txt').write_text(f'{int(arg)}\n')
                   return int(arg)

               file_path = pathlib.Path('/tmp/osCmdTest.txt')
               if file_path.exists():
                   return int(file_path.read_text().strip())
               return 0

           @self.command(addr=0x14, base=pr.Float(32))
           def CpuTempC(self, arg):
               # Optional Linux thermal-zone example (millidegrees C -> C).
               if arg is None:
                   thermal = pathlib.Path('/sys/class/thermal/thermal_zone0/temp')
                   if thermal.exists():
                       return float(thermal.read_text().strip()) / 1000.0
                   return -1.0
               return -1.0

OsMemMaster Device Pattern
==========================

``OsMemMaster`` is an example ``Device`` that defines typed
``RemoteVariable`` Nodes at offsets serviced by an ``OsCommandMemorySlave``.

In the example flow:

- ``OsMemMaster`` defines offsets/types for ``Uptime``, ``SysLoad*``, and
  ``FileTest``.
- ``MyCmdSlave`` (subclass of ``OsCommandMemorySlave``) implements matching
  callbacks at those offsets. It can also expose extra commands such as
  ``CpuTempC`` at another address.
- Variable reads/writes are executed as memory transactions through
  ``memBase=os_slave``.

.. code-block:: python

   import pyrogue as pr
   class OsMemMaster(pr.Device):
       def __init__(self, name='OsMemMaster', description='OS Memory Master Device', **kwargs):
           super().__init__(name=name, description=description, **kwargs)

           self.add(pr.RemoteVariable(
               name='Uptime',
               description='System Uptime In Seconds',
               offset=0x00,
               bitSize=32,
               base=pr.Float,
               mode='RO',
               pollInterval=1,
           ))

           self.add(pr.RemoteVariable(
               name='SysLoad1Min',
               description='1 Minute System Load',
               offset=0x04,
               bitSize=32,
               base=pr.Float,
               mode='RO',
               pollInterval=1,
           ))

           self.add(pr.RemoteVariable(
               name='SysLoad5Min',
               description='5 Minute System Load',
               offset=0x08,
               bitSize=32,
               base=pr.Float,
               mode='RO',
               pollInterval=1,
           ))

           self.add(pr.RemoteVariable(
               name='SysLoad15Min',
               description='15 Minute System Load',
               offset=0x0C,
               bitSize=32,
               base=pr.Float,
               mode='RO',
               pollInterval=1,
           ))

           self.add(pr.RemoteVariable(
               name='FileTest',
               description='File Read Write Test',
               offset=0x10,
               bitSize=32,
               base=pr.UInt,
               mode='RW',
           ))

           self.add(pr.RemoteVariable(
               name='CpuTempC',
               description='CPU Temperature In Degrees C (if available)',
               offset=0x14,
               bitSize=32,
               base=pr.Float,
               mode='RO',
               pollInterval=1,
           ))

   class ExampleRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           os_slave = MyCmdSlave()
           os_slave.setName('OsSlave')
           self.addInterface(os_slave)
           self.add(OsMemMaster(memBase=os_slave))

Operational Notes
=================

- Poll intervals on RO variables drive periodic reads through ``memBase``.
- Address offsets and ``base`` Model types must match across master/slave.
- This pattern is ideal for integration and prototyping, not high-rate paths.

API references
==============

- :doc:`/api/python/interfaces_oscommandmemoryslave`
- :doc:`/api/python/device`
- :doc:`/api/python/remotevariable`

Related Topics
==============

- Memory transaction topology and routing: :doc:`/memory_interface/index`
- Device lifecycle and managed startup: :doc:`/pyrogue_tree/core/device`
- Command behavior and callable Nodes: :doc:`/pyrogue_tree/core/command`
