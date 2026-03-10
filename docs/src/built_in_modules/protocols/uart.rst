.. _protocols_uart:

=============
UART Protocol
=============

UART-based memory access in Rogue is implemented by
``pyrogue.protocols.UartMemory`` in ``python/pyrogue/protocols/_uart.py``. The
interface adapts text-based serial register commands into Rogue memory
transactions.

Overview
========

``UartMemory`` implements ``rogue.interfaces.memory.Slave`` with 32-bit access
granularity and executes transactions on a worker thread.

Transaction model
=================

- Write transactions:
  each 32-bit word is sent as ``w <addr> <data>`` and validated from response.
- Read transactions:
  each 32-bit word is requested as ``r <addr>`` and returned data is written
  back into the transaction buffer.
- Non-zero status or malformed/empty responses raise transaction errors.

Threading and lifecycle
=======================

- Transactions are queued and processed in a dedicated worker thread.
- Implements Managed Interface Lifecycle:
  :ref:`pyrogue_tree_node_device_managed_interfaces`
- Posted writes are not supported by this implementation.

Common usage
============

- Low-rate control/monitor channels
- Bring-up/debug access paths on embedded hardware
- Systems exposing a simple UART register monitor/proxy in firmware

Code-backed example
===================

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

Integration notes
=================

- Confirm serial settings (baud/parity/stop bits) match endpoint firmware.
- Validate buffering/timing behavior when bridging UART into stream or command
  workflows.
- Keep transactions aligned to 32-bit words for predictable behavior.

Logging
=======

``UartMemory`` uses Python logging.

The logger name includes the serial device path:

- Pattern: ``pyrogue.UartMemory.<device>``
- Example: ``pyrogue.UartMemory./dev/ttyUSB0``

Configuration API:

.. code-block:: python

   import logging

   logging.getLogger('pyrogue.UartMemory').setLevel(logging.DEBUG)

The current implementation has several transaction-level debug statements in
the code commented out, so enabling the logger is most useful when those debug
calls are active or when additional UART diagnostics are added.
