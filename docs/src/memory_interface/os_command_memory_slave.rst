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

API reference
=============

See :doc:`/api/python/interfaces_oscommandmemoryslave` for generated API
details.
