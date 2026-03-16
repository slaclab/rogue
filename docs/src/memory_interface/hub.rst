.. _interfaces_memory_hub_ex:
.. _memory_interface_hub:

===================
Memory Hub Patterns
===================

A ``Hub`` sits between upstream memory initiators and downstream memory
responders. It can apply address offsets, group bus segments, translate one
addressing model into another, or split one incoming ``Transaction`` into
multiple downstream operations.

Most users do not need to subclass a raw ``Hub`` directly. In PyRogue,
``Device`` already builds on hub behavior and is the usual way to organize a
memory map. Custom ``Hub`` code becomes useful when the bus behavior itself must
be translated or manipulated.

Typical cases include paged register windows, composite address maps that need
special routing, or adaptation layers where one upstream transaction becomes
several downstream register operations.

What A ``Hub`` Does
===================

Compared with a plain ``Slave``, a ``Hub`` usually has two extra jobs:

- It exposes an upstream address window that may differ from the downstream one
- It may need to generate multiple downstream transactions to service one
  upstream request

That makes ``Hub`` the right abstraction whenever address translation is part of
the design.

Python Translation Hub Example
==============================

The example below sketches a paged translation device. Imagine a downstream
hardware block that exposes:

- An address register at ``0x100``
- A write-data register at ``0x104``
- A read-data register at ``0x108``

The ``Hub`` translates one upstream read or write request into those staged
register operations.

.. code-block:: python

   import pyrogue
   import rogue.interfaces.memory as rim

   class MyTranslationDevice(pyrogue.Device):
       def __init__(self, **kwargs):
           # Local register space is 12 bytes. Upstream transactions are fixed
           # at 4 bytes for this example.
           super().__init__(size=12, hubMin=4, hubMax=4, **kwargs)

       def _doTransaction(self, tran):
           # Serialize access because the staged protocol below is not safe for
           # overlapping transactions.
           with self._memLock:
               with tran.lock():
                   addr = tran.address().to_bytes(4, 'little', signed=False)

                   self._setError(0)

                   # Program the address register
                   tid = self._reqTransaction(self._getAddress() | 0x100,
                                              addr, 4, 0, rim.Write)
                   self._waitTransaction(tid)
                   if self._getError() != "":
                       tran.error(self._getError())
                       return

                   if tran.type() in (rim.Write, rim.Post):
                       data = bytearray(tran.size())
                       tran.getData(data, 0)

                       # Program the write-data register
                       tid = self._reqTransaction(self._getAddress() | 0x104,
                                                  data, 4, 0, rim.Write)
                       self._waitTransaction(tid)
                       if self._getError() != "":
                           tran.error(self._getError())
                       else:
                           tran.done()
                   else:
                       data = bytearray(tran.size())

                       # Read back from the read-data register
                       tid = self._reqTransaction(self._getAddress() | 0x108,
                                                  data, 4, 0, rim.Read)
                       self._waitTransaction(tid)
                       if self._getError() != "":
                           tran.error(self._getError())
                       else:
                           tran.setData(data, 0)
                           tran.done()

This pattern is often easier to integrate as a ``Device`` than as a raw
``Hub``, because the ``Device`` participates naturally in the normal PyRogue
tree and already carries locking and address-map structure with it.

Using A Python Device Hub
=========================

Once the translation logic is packaged as a ``Device``, it can be inserted into
an ordinary PyRogue tree like any other node. That is usually the most useful
way to deploy a hub-style translation layer in practice.

.. code-block:: python

   import pyrogue

   class ExampleRoot(pyrogue.Root):
       def __init__(self):
           super().__init__(name="MyRoot")

           # Add an FPGA-facing device at 0x1000 that contains the staged
           # paged-memory interface used by the translation device.
           self.add(SomeFpgaDevice(name="Fpga", offset=0x1000))

           # Add the translation device at relative offset 0x10 within Fpga.
           # Its downstream base address becomes 0x1010, while it exposes its
           # own translated upstream address space to child devices.
           self.Fpga.add(MyTranslationDevice(name="TranBase", offset=0x10))

           # Add a child device that exists in the translated address space
           # managed by TranBase.
           self.TranBase.add(SomeDevice(name="DevA", offset=0x200))

In this arrangement, ``TranBase`` acts as an address-space boundary inside the
tree. Upstream code interacts with child devices beneath ``TranBase`` using the
translated address map, while the ``MyTranslationDevice`` implementation
converts those accesses into the staged downstream register operations required
by the hardware block.

C++ Hub Example
===============

The old documentation had a much better raw ``Hub`` example here, because it
showed the mechanics of translating one upstream ``Transaction`` into staged
downstream accesses. That level of detail is useful, so the example below
brings that style back in a cleaned-up form.

.. code-block:: cpp

   #include <array>
   #include <mutex>
   #include "rogue/interfaces/memory/Hub.h"
   #include "rogue/interfaces/memory/Constants.h"

   namespace rim = rogue::interfaces::memory;

   class MyHub : public rim::Hub {
   public:
      using Ptr = std::shared_ptr<MyHub>;
      static Ptr create() { return std::make_shared<MyHub>(); }

      MyHub() : rim::Hub(0) {}

      // The paged protocol below is not safe for overlapping transactions,
      // so serialize access through the Hub.
      std::mutex lock_;

      void doTransaction(rim::TransactionPtr tran) override {
         std::lock_guard<std::mutex> lock(lock_);
         auto tranLock = tran->lock();

         uint32_t tid;
         std::array<uint8_t, 4> addrBytes{};

         // The address seen by the Hub is relative to its upstream window.
         const uint32_t addr = static_cast<uint32_t>(tran->address());
         addrBytes[0] = static_cast<uint8_t>((addr >> 0)  & 0xFF);
         addrBytes[1] = static_cast<uint8_t>((addr >> 8)  & 0xFF);
         addrBytes[2] = static_cast<uint8_t>((addr >> 16) & 0xFF);
         addrBytes[3] = static_cast<uint8_t>((addr >> 24) & 0xFF);

         // Clear any previous downstream error state.
         setError("");

         // Program the downstream address register at offset 0x100.
         tid = reqTransaction(getAddress() | 0x100, 4, addrBytes.data(), rim::Write);
         waitTransaction(tid);
         if (getError() != "") {
            tran->error(getError());
            return;
         }

         // Handle write and posted-write requests by staging the write data
         // into the downstream data register at offset 0x104.
         if (tran->type() == rim::Write || tran->type() == rim::Post) {
            tid = reqTransaction(getAddress() | 0x104,
                                 tran->size(),
                                 tran->begin(),
                                 rim::Write);
            waitTransaction(tid);

            if (getError() != "") {
               tran->error(getError());
            } else {
               tran->done();
            }
         }

         // Handle read and verify-read requests by pulling data from the
         // downstream read-data register at offset 0x108.
         else {
            tid = reqTransaction(getAddress() | 0x108,
                                 tran->size(),
                                 tran->begin(),
                                 rim::Read);
            waitTransaction(tid);

            if (getError() != "") {
               tran->error(getError());
            } else {
               tran->done();
            }
         }
      }
   };

Design Notes
============

The most important design question for a custom ``Hub`` is whether the incoming
thread should block while downstream work completes. The example above does
block, which keeps the flow easy to follow but also means only one staged
transaction can be in progress at a time. In simple register-window protocols
that is often acceptable. In more complex or slower bus paths, it may be better
to queue the work and complete it asynchronously.

If the design forwards data pointers from the original ``Transaction`` into
downstream work, lock scope and object lifetime need especially careful
attention. In many cases it is safer to copy the data into a new local buffer,
even if that costs some performance.

Logging
=======

The base Rogue memory ``Hub`` uses Rogue C++ logging with the logger name
``pyrogue.memory.Hub``.

- Logger name: ``pyrogue.memory.Hub``
- Unified Logging API:
  ``logging.getLogger('pyrogue.memory.Hub').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.memory.Hub', rogue.Logging.Debug)``
You can enable that logger before or after constructing the object. Enable it
before construction only if you want constructor or early startup visibility
into the base hub behavior:


For custom ``Hub`` subclasses, it is often worth adding a second
subclass-specific logger if the translation or split logic is non-trivial.

What To Explore Next
====================

- Connection and addressing patterns: :doc:`/memory_interface/connecting`
- Asynchronous completion patterns in ``Slave`` implementations:
  :doc:`/memory_interface/slave`
- Transaction lifecycle details: :doc:`/memory_interface/transactions`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/memory/hub`

- C++:

  - :doc:`/api/cpp/interfaces/memory/hub`
