.. _interfaces_memory_master_ex:
.. _memory_interface_master:

======================
Memory Master Patterns
======================

In most applications, PyRogue ``RemoteVariable``/``Device`` APIs hide direct
master usage. Custom masters are useful when software must issue explicit
transaction sequences.

Typical master flow
===================

1. Clear previous error state.
2. Request transaction(s) at address/size/type.
3. Wait for completion.
4. Check error and continue or fail.

Python example
==============

.. code-block:: python

   import rogue.interfaces.memory as rim

   class MyMemMaster(rim.Master):
       def __init__(self):
           super().__init__()

       def inc_at_address(self, address: int, delta: int) -> bool:
           data = bytearray(4)

           self._clearError()
           tid = self._reqTransaction(address, data, 4, 0, rim.Read)
           self._waitTransaction(tid)

           if self._getError() != "":
               return False

           value = int.from_bytes(data, 'little', signed=False) + delta
           data = value.to_bytes(4, 'little', signed=False)

           tid = self._reqTransaction(address, data, 4, 0, rim.Write)
           self._waitTransaction(tid)
           return self._getError() == ""

C++ example
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

         clearError();

         uint32_t tid = reqTransaction(address, 4, &value, rim::Read);
         waitTransaction(tid);
         if (getError() != "") return false;

         value += delta;
         tid = reqTransaction(address, 4, &value, rim::Write);
         waitTransaction(tid);
         return getError() == "";
      }
   };

Notes
=====

- Read-modify-write sequences are not atomic by default across external actors.
- Higher-level PyRogue locking and device models should coordinate shared
  access when required.

Logging
=======

The base Rogue memory master uses Rogue C++ logging with the static logger
name:

- ``pyrogue.memory.Master``

Enable it before constructing or using the master:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.memory.Master', rogue.Logging.Debug)

This logger is useful for transaction-request and error-path debugging in
custom master implementations. The base ``Master`` class does not provide a
separate runtime debug helper.

What to explore next
====================

- Transaction lifecycle details: :doc:`/memory_interface/transactions`
- Slave implementation patterns: :doc:`/memory_interface/slave`
- Hub routing/translation: :doc:`/memory_interface/hub`
