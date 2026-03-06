.. _interfaces_python_os_command_memory_slave:

====================
OsCommandMemorySlave
====================

:py:class:`~pyrogue.interfaces.OsCommandMemorySlave` is a memory ``Slave`` that
maps read/write transactions to Python callables keyed by address.

This is useful when an upstream memory master needs command-like behavior
through the memory transport path.

Typical behavior:

- Write/Post transaction: decode payload bytes with the configured ``Model``,
  then call the registered function with the decoded argument.
- Read transaction: call the function, encode the return value with the
  configured ``Model``, and return bytes in the response.

Commands are registered with the ``command(addr, base)`` decorator, where
``base`` provides ``toBytes``/``fromBytes`` conversion.

How Transaction Mapping Works
=============================

Each registered address defines one callable with the signature
``func(self, arg)``.

- For write/post transactions, ``arg`` is decoded from transaction bytes using
  the command ``base`` Model.
- For read transactions, ``arg`` is ``None`` and the return value is encoded
  back into bytes with the same Model.

The transaction is marked done on success. Exceptions are propagated to the
transaction as error responses.

Minimal Pattern
===============

.. code-block:: python

   import pyrogue as pr
   import pyrogue.interfaces as pri

   class MyCmdSlave(pri.OsCommandMemorySlave):
       def __init__(self):
           super().__init__(minWidth=4, maxSize=256)
           self._counter = 0

           @self.command(addr=0x00, base=pr.UInt(32))
           def Counter(self, arg):
               if arg is None:
                   return self._counter
               self._counter = int(arg)

           @self.command(addr=0x04, base=pr.UInt(32))
           def Increment(self, arg):
               if arg is not None:
                   self._counter += int(arg)
               return self._counter

Common Use Cases
================

- Expose host-side process state through a memory path.
- Bridge command-like actions into bus-oriented control flows.
- Prototype firmware-like register behaviors in pure Python.

Related Example
===============

For a complete paired example, see:

- :doc:`/pyrogue_tree/builtin_devices/osmemmaster`

API reference
=============

See :doc:`/api/python/interfaces_oscommandmemoryslave` for generated API
details.
