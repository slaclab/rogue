.. _interfaces_memory_slave_ex:
.. _memory_interface_slave:

=====================
Memory Slave Patterns
=====================

Custom memory ``Slave`` objects are common when Rogue needs to adapt a
proprietary hardware or protocol engine to the Rogue transaction model.

Unlike custom ``Master`` implementations, custom ``Slave`` implementations are
fairly common because they often provide the hardware-facing side of the bus.
They are the place where incoming Rogue ``Transaction`` objects are translated
into the real protocol operations required by a device or transport.

Python and C++ subclasses of ``Slave`` can be mixed freely with upstream
``Master`` implementations in either language.

Typical Slave Flow
==================

Most custom ``Slave`` code follows this pattern:

1. Receive a ``Transaction`` in ``_doTransaction`` or ``doTransaction``.
2. Store the ``Transaction`` if completion will be asynchronous.
3. Dispatch the actual protocol read or write.
4. On callback, recover the stored ``Transaction``.
5. Check whether it is still valid, then set data, report error, or call
   ``done()``.

Assume, for example, that the underlying protocol provides calls such as
``protocolRead(id, address, size)`` and ``protocolWrite(id, address, size,
data)``, with callbacks when the operation completes.

At the ``Slave`` boundary, ``Write`` and ``Post`` often arrive with the same
basic shape: both carry outbound write data. That is why many implementations
branch on them together. The distinction is that ``Post`` is still a different
transaction type, so a ``Slave`` can choose to give it different treatment if
the downstream protocol cares about posted-write semantics.

Python Example
==============

.. code-block:: python

   import rogue.interfaces.memory as rim

   class MyMemSlave(rim.Slave):

       # Assume our minimum size is 4 bytes and our maximum size is 1024 bytes
       def __init__(self):
           super().__init__(4, 1024)

       # Entry point for incoming transactions
       def _doTransaction(self, tran):
           with tran.lock():
               # Store the Transaction so it can be recovered on callback
               self._addTransaction(tran)

               if tran.type() in (rim.Write, rim.Post):
                   data = bytearray(tran.size())
                   tran.getData(data, 0)
                   protocolWrite(tran.id(), tran.address(), tran.size(), data)
               else:
                   protocolRead(tran.id(), tran.address(), tran.size())

       # Protocol callback for write completion
       def protocolWriteDone(self, tid, ok):
           tran = self._getTransaction(tid)
           if tran is None:
               return

           with tran.lock():
               if tran.expired():
                   return

               if not ok:
                   tran.error("protocol write failed")
               else:
                   tran.done()

       # Protocol callback for read completion
       def protocolReadDone(self, tid, data, ok):
           tran = self._getTransaction(tid)
           if tran is None:
               return

           with tran.lock():
               if tran.expired():
                   return

               if not ok:
                   tran.error("protocol read failed")
               else:
                   tran.setData(data, 0)
                   tran.done()

The important part of this pattern is that the incoming ``Transaction`` is kept
alive until the underlying protocol completes. That is why ``_addTransaction()``
and ``_getTransaction()`` are used here.

This example intentionally handles ``Write`` and ``Post`` the same way. That is
common. A different protocol could instead inspect ``tran.type()`` and apply a
special posted-write policy.

C++ Example
===========

.. code-block:: cpp

   #include <algorithm>
   #include "rogue/interfaces/memory/Constants.h"
   #include "rogue/interfaces/memory/Slave.h"

   namespace rim = rogue::interfaces::memory;

   class MyMemSlave : public rim::Slave {
   public:
      using Ptr = std::shared_ptr<MyMemSlave>;
      static Ptr create() { return std::make_shared<MyMemSlave>(); }

      MyMemSlave() : rim::Slave(4, 1024) {}

      void doTransaction(rim::TransactionPtr tran) override {
         auto lock = tran->lock();
         addTransaction(tran);

         if (tran->type() == rim::Write || tran->type() == rim::Post) {
            protocolWrite(tran->id(), tran->address(), tran->size(), tran->begin());
         } else {
            protocolRead(tran->id(), tran->address(), tran->size());
         }
      }

      void protocolWriteDone(uint32_t id, bool ok) {
         auto tran = getTransaction(id);
         if (tran == nullptr) return;

         auto lock = tran->lock();
         if (tran->expired()) return;

         if (!ok) {
            tran->error("protocol write failed");
         } else {
            tran->done();
         }
      }

      void protocolReadDone(uint32_t id, uint8_t* data, bool ok) {
         auto tran = getTransaction(id);
         if (tran == nullptr) return;

         auto lock = tran->lock();
         if (tran->expired()) return;

         if (!ok) {
            tran->error("protocol read failed");
         } else {
            std::copy(data, data + tran->size(), tran->begin());
            tran->done();
         }
      }
   };

Design Notes
============

Asynchronous completion is the central design issue for custom ``Slave``
implementations. If the underlying protocol does not complete immediately, the
``Transaction`` must be stored and recovered later. Before completing it, always
check whether it has expired.

This is also why lock scope matters. A lock should protect access to the shared
``Transaction`` state, but it should not accidentally serialize unrelated work
longer than necessary.

Logging
=======

The base Rogue memory ``Slave`` does not define a dedicated logger name of its
own. In practice, logging is usually added by concrete subclasses or protocol
layers built on top of ``Slave``.

For custom implementations, the recommended pattern is:

- Python: add a logger with ``pyrogue.logInit(...)``
- C++: add a logger with ``rogue::Logging::create("...")``

That gives users a stable logger name they can filter while debugging the
protocol-specific behavior of the ``Slave``.

What To Explore Next
====================

- Transaction internals and locking: :doc:`/memory_interface/transactions`
- ``Hub`` translation patterns: :doc:`/memory_interface/hub`
- Bus connection patterns: :doc:`/memory_interface/connecting`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/memory/slave`

- C++:

  - :doc:`/api/cpp/interfaces/memory/slave`
