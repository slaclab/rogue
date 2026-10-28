.. _interfaces_memory_master_ex:
.. _memory_interface_master:

======================
Memory Master Patterns
======================

In most applications, higher-level PyRogue interfaces such as
``RemoteVariable``, ``Device``, and ``RemoteCommand`` hide direct ``Master``
usage. Custom memory ``Master`` objects become useful when software needs to
issue explicit transaction sequences at the bus level.

Typical cases include test utilities, low-level initialization flows, protocol
adaptors, or software components that must perform a read-modify-write sequence
without going through a higher-level PyRogue object model.

Python and C++ subclasses of ``Master`` can be mixed freely with downstream
``Slave`` implementations in either language. That makes it practical to
prototype a transaction source in Python and move it into C++ later if needed.

Typical Master Flow
===================

Most custom ``Master`` code follows the same basic pattern:

1. Clear any previous error state.
2. Request one or more transactions at a given address, size, and type.
3. Wait for each transaction to complete.
4. Check for error state before continuing.

The transaction type passed to ``reqTransaction`` or ``_reqTransaction`` is one
of the key choices in custom ``Master`` code. ``Read`` and ``Write`` are the
most common, but ``Post`` is also available as a distinct posted-write
transaction type. In the code, that means the downstream path can see
``Post`` instead of ``Write`` and apply different behavior. Some
implementations handle ``Post`` exactly like ``Write``. Others use it for
write paths that should not wait for a normal downstream response.

Python Example
==============

The example below issues a read, increments the 32-bit value at the target
address, and then writes the updated value back.

.. code-block:: python

   import rogue.interfaces.memory as rim

   class MyMemMaster(rim.Master):

       # Init method must call the parent class init
       def __init__(self):
           super().__init__()

       # Increment the 32-bit value stored at the target address
       def inc_at_address(self, address: int, delta: int) -> bool:

           # Local buffer for the read transaction
           data = bytearray(4)

           # Clear any existing error state
           self._clearError()

           # Start the read transaction and wait for completion
           tid = self._reqTransaction(address, data, 4, 0, rim.Read)
           self._waitTransaction(tid)

           if self._getError() != "":
               return False

           # Modify the returned data locally
           value = int.from_bytes(data, 'little', signed=False)
           value += delta
           data = value.to_bytes(4, 'little', signed=False)

           # Write the updated value back to the same address
           tid = self._reqTransaction(address, data, 4, 0, rim.Write)
           self._waitTransaction(tid)

           return self._getError() == ""

This example is intentionally simple. It shows the mechanics of issuing and
waiting on transactions, but it does not make the read-modify-write sequence
atomic with respect to other actors on the bus.

C++ Example
===========

.. code-block:: cpp

   #include "rogue/interfaces/memory/Constants.h"
   #include "rogue/interfaces/memory/Master.h"

   namespace rim = rogue::interfaces::memory;

   class MyMemMaster : public rim::Master {
   public:
      using Ptr = std::shared_ptr<MyMemMaster>;
      static Ptr create() { return std::make_shared<MyMemMaster>(); }

      bool incAtAddress(uint64_t address, uint32_t delta) {
         uint32_t value = 0;

         // Clear any existing error state
         clearError();

         // Read the current 32-bit value
         uint32_t tid = reqTransaction(address, 4, &value, rim::Read);
         waitTransaction(tid);
         if (getError() != "") return false;

         // Update it locally
         value += delta;

         // Write the updated value back
         tid = reqTransaction(address, 4, &value, rim::Write);
         waitTransaction(tid);
         return getError() == "";
      }
   };

Posted Write Example
====================

When a target register or command path should be driven using a posted write,
the only code change may be the transaction type itself.

.. code-block:: python

   import rogue.interfaces.memory as rim

   class MyMemMaster(rim.Master):
       def __init__(self):
           super().__init__()

       def trigger(self, address: int) -> bool:
           data = bytearray([1, 0, 0, 0])

           self._clearError()
           tid = self._reqTransaction(address, data, 4, 0, rim.Post)
           self._waitTransaction(tid)

           return self._getError() == ""

At the memory-interface layer, ``Post`` is a first-class transaction type. A
downstream ``Slave`` or ``Hub`` may handle it the same way as ``Write`` or may
apply different policy depending on the protocol or hardware design.

Design Notes
============

Read-modify-write sequences are not automatically atomic across external actors.
If other software or hardware can touch the same address in the middle of the
sequence, higher-level locking or coordination is required. In many PyRogue
applications that coordination is handled at the device-tree level rather than
inside the raw ``Master`` implementation.

Logging
=======

The base Rogue memory ``Master`` uses Rogue C++ logging with the logger name
``pyrogue.memory.Master``.

- Logger name: ``pyrogue.memory.Master``
- Unified Logging API:
  ``pyrogue.setLogLevel('pyrogue.memory.Master', 'DEBUG')``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.memory.Master', rogue.Logging.Debug)``

You can enable that logger before or after constructing the object. Enable it
before construction only if you want constructor or early startup messages from
the base implementation:


``Master`` does not expose a separate runtime debug helper. For more detailed
custom logging, add subclass-specific logging around transaction sequencing and
error handling.

What To Explore Next
====================

- Transaction lifecycle details: :doc:`/memory_interface/transactions`
- Custom ``Slave`` patterns: :doc:`/memory_interface/slave`
- ``Hub`` translation patterns: :doc:`/memory_interface/hub`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/memory/master`

- C++:

  - :doc:`/api/cpp/interfaces/memory/master`
