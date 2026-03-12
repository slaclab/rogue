.. _interfaces_memory_slave_ex:
.. _memory_interface_slave:

=====================
Memory Slave Patterns
=====================

Custom slaves are common when adapting proprietary protocols or hardware
engines to Rogue's transaction model.

Typical slave flow
==================

1. Receive ``Transaction`` in ``_doTransaction``/``doTransaction``.
2. Store transaction handle if completion is asynchronous.
3. Dispatch protocol read/write request.
4. On callback, recover transaction, validate freshness, set data/error, and
   call ``done()``.

Python skeleton example
=======================

.. code-block:: python

   import rogue.interfaces.memory as rim

   class MyMemSlave(rim.Slave):
       def __init__(self):
           super().__init__(4, 1024)  # min/max transaction sizes

       def _doTransaction(self, tran):
           with tran.lock():
               self._addTransaction(tran)

               if tran.type() in (rim.Write, rim.Post):
                   data = bytearray(tran.size())
                   tran.getData(data, 0)
                   protocolWrite(tran.id(), tran.address(), tran.size(), data)
               else:
                   protocolRead(tran.id(), tran.address(), tran.size())

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

C++ skeleton example
====================

.. code-block:: cpp

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

Logging
=======

``memory.Slave`` does not define a dedicated logger of its own. Logging is
typically implemented by concrete subclasses or bridge layers built on top of
``Slave``.

Examples elsewhere in Rogue include:

- ``pyrogue.SrpV0``
- ``pyrogue.SrpV3``
- ``pyrogue.memory.TcpClient.<addr>.<port>``

For custom slaves, the recommended pattern is:

- Python: add ``self._log`` with ``pyrogue.logInit(...)``
- C++: add ``rogue::Logging::create("...")``

This gives users a stable logger name they can filter.

What to explore next
====================

- Transaction internals and locking: :doc:`/memory_interface/transactions`
- Hub translation strategies: :doc:`/memory_interface/hub`
- Bus connection patterns: :doc:`/memory_interface/connecting`

API Reference
=============

- Python: :doc:`/api/python/rogue/interfaces/memory/slave`
- C++: :doc:`/api/cpp/interfaces/memory/slave`
