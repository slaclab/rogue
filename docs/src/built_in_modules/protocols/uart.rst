.. _protocols_uart:

===========
UART Memory
===========

For simple serial register access, PyRogue provides
``pyrogue.protocols.UartMemory``. This helper adapts a text-based UART command
protocol into Rogue memory transactions, making it useful for low-rate control
and monitor channels, bring-up paths on embedded hardware, and systems that
expose a simple UART register monitor in firmware.

``UartMemory`` lives in the ``pyrogue.protocols`` namespace and implements a
memory ``Slave`` with 32-bit access granularity. Transactions are queued and
processed on a dedicated worker thread, so the interface can participate in the
managed ``Root`` lifecycle through ``addInterface()`` or ``addProtocol()``.

Transaction Model
=================

Each write transaction is split into 32-bit words and sent as
``w <addr> <data>``. Each read or verify transaction is split the same way and
issued as ``r <addr>``. Returned data is packed back into the transaction
buffer in little-endian form. Empty responses, malformed responses, or non-zero
status values are reported as transaction errors. Posted writes are not
supported by this implementation.

Configuration Example
=====================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.protocols

   class UartRegBlock(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           # Add RemoteVariable definitions here for your UART-backed register map.


   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot')

           uart_mem = pyrogue.protocols.UartMemory(
               '/dev/ttyUSB0',
               115200,
               timeout=1.0,
           )

           self.add(UartRegBlock(
               name='UartRegs',
               offset=0x0,
               memBase=uart_mem,
           ))

Key Constructor Arguments
=========================

- ``device`` selects the serial port path, such as ``/dev/ttyUSB0``.
- ``baud`` selects the UART baud rate.
- ``timeout`` controls line-read timeout behavior.
- Additional keyword arguments are passed through to ``serial.Serial`` for
  platform-specific serial settings.

Operational Notes
=================

Confirm that serial settings such as baud, parity, and stop bits match the
endpoint firmware. Keep transactions aligned to 32-bit words for predictable
behavior, because the implementation always operates one 32-bit word at a time.
This interface is best suited to low-rate memory access rather than bulk data
paths.

Logging
=======

``UartMemory`` uses Python logging. The logger name includes the serial device
path, following the pattern ``pyrogue.UartMemory.<device>``.

- Pattern: ``pyrogue.UartMemory.<device>``
- Example: ``pyrogue.UartMemory./dev/ttyUSB0``

.. code-block:: python

   import pyrogue

   pyrogue.setLogLevel('pyrogue.UartMemory', 'DEBUG')

The current implementation has several transaction-level debug statements in
the code commented out, so enabling the logger is most useful when those debug
calls are active or when additional UART diagnostics are added.

Related Topics
==============

- Memory-style transaction flow: :doc:`/memory_interface/index`
- Managed interface lifecycle: :ref:`pyrogue_tree_node_device_managed_interfaces`

API Reference
=============

- Python:

  - :doc:`/api/python/pyrogue/protocols/uartmemory`
