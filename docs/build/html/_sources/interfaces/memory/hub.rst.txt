.. _interfaces_memory_hub_ex:

==================
Memory Hub Example
==================

The memory Hub interfaces between an upstream memory Master object and a downstream Memory
slave object. The Hub can be used to group Masters together with a common offset, as is done
in the pyrogue.Device class. It can also be used to manipulate a memory bus transaction.

Most users will not need to modify or sub-class a memory hub. Instead the Device python class,
which is a sub-class of the Hub, will be used to organize the memory map. In some special cases
complicated hardware interface layers will need to be supported and a special Hub will need to be created.

In this example we service incoming read and write requests and forward them to a memory
slave which implements a paged memory space. This means there is a write register for the
address (0x100), a write register for the write data (0x104), and a read register for
read data (0x108). This example is not very efficient in that it only allows a single
transaction to be executed at a time.

See :ref:`interfaces_memory_hub` for more detail on the Hub class.

Python Raw Hub Example
======================

Below is an example of creating a raw Hub device which translates memory
transactions in Python.

.. code-block:: python

    import pyrogue
    import rogue.interfaces.memory

    # Create a subclass of a memory Hub
    # This hub has an offset of 0
    class MyHub(rogue.interfaces.memory.Hub):

        # Init method must call the parent class init
        def __init__(self):

            # Here we set the offset and a new root min and
            # max transaction size
            super().__init__(0,4,4)

            # Create a lock
            self._lock = threading.Lock()

        # Entry point for incoming transaction
        def _doTransaction(self,transaction):

            # First lock the memory space to avoid
            # overlapping paged transactions
            with self._lock:

               # Next we lock the transaction data
               # Here it is held until the downstream transaction completes.
               with transaction.lock():

                   # Put address into byte array, we do this because we will
                   # need to pass it as the data field of a transaction later
                   # The address the HUB sees is always relative, not absolute
                   addr = transaction.address().to_bytes(4, 'little', signed=False)

                   # Clear any existing errors
                   self._setError(0)

                   # Create transaction setting address register (offset 0x100)
                   id = self._reqTransaction(self._getAddress() | 0x100, addr, 4, 0, rogue.interfaces.memory.Write)

                   # Wait for transaction to complete
                   self._waitTransaction(id)

                   # Check transaction result, forward error to incoming transaction
                   if self._getError() != "":
                       transaction.error(self._getError())
                       return False

                   # Handle write or post
                   if transaction.type() == rogue.interfaces.memory.Write or
                      transaction.type() == rogue.interfaces.memory.Post:

                      # Copy data into byte array
                      data = bytearray(transaction.size())
                      transaction.getData(data,0)

                      # Create transaction setting write data register (offset 0x104)
                      id = self._reqTransaction(self._getAddress() | 0x104, data, 4, 0, rogue.interfaces.memory.Write)

                      # Wait for transaction to complete
                      self._waitTransaction(id)

                      # Check transaction result, forward error to incoming transaction
                      if self._getError() != "":
                          transaction.error(self._getError())
                          return False

                      # Success
                      transaction.done()

                   # Handle read or verify read
                   else:

                      # Create read data byte array
                      data = bytearray(transaction.size())

                      # Create transaction reading read data register (offset 0x108)
                      id = self._reqTransaction(self._getAddress() | 0x108, data, 4, 0, rogue.interfaces.memory.Read)

                      # Wait for transaction to complete
                      self._waitTransaction(id)

                      # Check transaction result, forward error to incoming transaction
                      if self._getError() != "":
                          transaction.error(self._getError())
                          return False

                      # Copy data into original transaction and complete
                      transaction.setData(data,0)
                      transaction.done()


Python Device Hub Example
=========================

Below is an example of implementing the above example in a Device subclass. This allows
the Hub to interact in a standard PyRogue tree. It will have its own base address and
size in the downstream address map, but expose a separate upstream address map for
translated transactions. More information about the Device class is included at TBD.

.. code-block:: python

    import pyrogue
    import rogue.interfaces.memory

    # Create a subclass of a Device
    class MyTranslationDevice(pyrogue.Device):

        # Init method with the same signature as a Device
        def __init__(self, *,
                     name=None,
                     description='',
                     memBase=None,
                     offset=0,
                     hidden=False,
                     expand=True,
                     enabled=True,
                     enableDeps=None):

            # Setup base class with size of 3*8 bytes for our local 3 registers and a
            # upstream min and max transaction size of 4 bytes.
            super().__init__(name=name, description=description, memBase=memBase,
                             offset=offset, hidden=hidden, expand=expand, enabled=enabled,
                             enableDeps=enableDeps, size=12, hubMin=4, hubMax=4)

        # Same code from previous section with the exception that the existing Device
        # lock is used instead of a separate lock as above.
        def _doTransaction(self,transaction):

            # First lock the memory space to avoid
            # overlapping paged transactions
            with self._memLock:

Using Python Device Hub
=======================

Below is an example of how the above Device would be used in a PyRogue tree.
More information about the PyRogue Root class is included at TBD.

.. code-block:: python

    import pyrogue

    class ExampleRoot(pyrogue.Root):

        def __init__(self):
            super().__init__(name="MyRoot")

            # Add FPGA device at 0x1000 which hosts paged master
            self.add(SomeFpgaDevice(name="Fpga", offset=0x1000))

            # Add our translation device to the FPGA with relative offset 0x10
            # its new address becomes 0x1010 and it owns a new address space
            self.Fpga.add(MyTranslationDevice(name="TranBase", offset=0x10))

            # Add sub device which exists in paged address space
            # its address is 0x200 in the spaced mastered by TranBase
            self.TranBase.add(SomeDevice(name="devA", offset=0x200))


C++ Raw Hub Example
===================

Below is an example of creating a raw Hub device which translates memory
transactions in C++.

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <rogue/interfaces/memory/Hub.h>
   #include <boost/thread.hpp>

   // Create a subclass of a memory Hub
   class MyHub : public rogue::interfaces::memory::Hub {

         // Mutex
         boost::mutex mtx_;

      public:

         // Create a static class creator to return our custom class
         // wrapped with a shared pointer
         static boost::shared_ptr<MyHub> create() {
            static boost::shared_ptr<MyHub> ret =
               boost::make_shared<MyHub>();
            return(ret);
         }

         // Standard class creator which is called by create
         // Here we set offset
         MyHub() : rogue::interfaces::memory::Hub(0) {}

         // Entry point for incoming transaction
         void doTransaction(rogue::interfaces::memory::TransactionPtr tran) {
            uint32_t id;

            // First lock the memory space to avoid overlapping paged transactions
            boost::lock_guard<boost::mutex> lock(slaveMtx_);

            // Next we lock the transaction data with a scoped lock
            rogue::interfaces::memory::TransactionLockPtr lock = tran->lock();

            // Clear any existing errors
            this->setError(0)

            // Create transaction setting address register (offset 0x100)
            // The address the HUB sees is always relative, not absolute
            id = this->reqTransaction(this->getAddress() | 0x100, 4, transaction->address(),
                                      rogue::interfaces::memory::Write);

            // Wait for transaction to complete
            this->waitTransaction(id);

            // Check transaction result, forward error to incoming transaction
            if ( this->getError() != "" ) {
               transaction->error(this->getError());
               return false
            }

            // Handle write or post
            if ( tran->type() == rogue::interfaces::memory::Write ||
                 tran->type() == rogue::interfaces::memory::Post ) {

               // Create transaction setting write data register (offset 0x104)
               // Forward data pointer from original transaction
               id = this->reqTransaction(this->getAddress() | 0x104, 4, transaction->begin(),
                                         rogue::interfaces::memory::Write);

               // Wait for transaction to complete
               this->waitTransaction(id);

               // Check transaction result, forward error to incoming transaction
               if ( this->getError() != "" ) {
                  transaction->error(this->getError());
                  return false
               }
               else transaction->done();
            }

            // Handle read or verify read
            else {

               // Create transaction getting read data register (offset 0x108)
               // Forward data pointer from original transaction
               id = this->reqTransaction(this->getAddress() | 0x104, 4, transaction->begin(),
                                         rogue::interfaces::memory::Write);

               // Wait for transaction to complete
               this->waitTransaction(id);

               // Check transaction result, forward error to incoming transaction
               if ( this->getError() != "" ) {
                  transaction->error(this->getError());
                  return false
               }
               else transaction->done();
            }

   };

A few notes on the above examples.

The incoming transaction source thread will be stalled as we wait
on the downstream transaction to complete. It may be better to queue the transaction and service
it with a separate thread. Also in the C++ example the original data buffer is passed to the
new transaction. This requires that the lock be held on the transaction until the downstream
transaction is complete. Instead it may be better to create a new buffer and copy the data
as is done in the Python example. See the :ref:`interfaces_memory_slave_ex` example for
ways to store and later retrieve the Transaction record while the downstream transaction is
in progress.

