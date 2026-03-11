.. _interfaces_memory_hub_ex:
.. _memory_interface_hub:

===================
Memory Hub Patterns
===================

A ``Hub`` sits between upstream masters and downstream slaves. It can apply
address offsets, group bus segments, and split/translate transactions.

Most users rely on ``pyrogue.Device`` (a hub-based abstraction) instead of
subclassing raw hub classes directly.

When custom hubs are useful
===========================

- Paged/register-window protocols that require address/data staging.
- Composite address maps requiring transaction routing/splitting.
- Protocol adaptation layers where one upstream request becomes multiple
  downstream requests.

Python translation hub sketch
=============================

.. code-block:: python

   import pyrogue
   import rogue.interfaces.memory as rim

   class MyHub(pyrogue.Device):
       def __init__(self, **kwargs):
           super().__init__(size=12, hubMin=4, hubMax=4, **kwargs)

       def _doTransaction(self, tran):
           with self._memLock:
               with tran.lock():
                   # Translate incoming transaction into staged register ops
                   # against downstream bus windows, then set data/done/error.
                   pass

C++ hub sketch
==============

.. code-block:: cpp

   #include "rogue/interfaces/memory/Hub.h"

   namespace rim = rogue::interfaces::memory;

   class MyHub : public rim::Hub {
   public:
      using Ptr = std::shared_ptr<MyHub>;
      static Ptr create() { return std::make_shared<MyHub>(); }

      MyHub() : rim::Hub(0) {}

      void doTransaction(rim::TransactionPtr tran) override {
         auto lock = tran->lock();
         // Translate / split / forward transaction(s) here.
      }
   };

Design notes
============

- Keep lock scope explicit when forwarding asynchronous downstream requests.
- If downstream completion is deferred, store/recover transaction handles
  carefully and check ``expired()`` before completion.
- Prefer device-level composition unless raw hub control is required.

Logging
=======

The base Rogue memory hub uses Rogue C++ logging.

- Logger name: ``pyrogue.memory.Hub``
- Configuration API:
  ``rogue.Logging.setFilter('pyrogue.memory.Hub', rogue.Logging.Debug)``

Set the filter before constructing the hub:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.memory.Hub', rogue.Logging.Debug)

For custom hub subclasses, it is often worth adding a second subclass-specific
logger in addition to the base hub logger if your translation logic is complex.

API reference
=============

- Python: :doc:`/api/python/interfaces_memory_hub`
- C++: :doc:`/api/cpp/interfaces/memory/hub`

What to explore next
====================

- Connection and addressing patterns: :doc:`/memory_interface/connecting`
- Async completion in slave implementations: :doc:`/memory_interface/slave`
- Transaction lifecycle and subtransactions: :doc:`/memory_interface/transactions`
