.. _interfaces_memory_master_ex:

=====================
Memory Master Example
=====================

In most cases the user will take advantage of the pyrogue.RemoteVariable, 
pyrogue.Device, pyrogue.RemoteCommand and pyrogue.MemoryBlock classes to
interact with memory buses. In rare cases it may be necessary to write
custom memory Master modules in Python or C++.

Python and C++ subclasses of the Master class can be used interchangeably, 
allowing c++ Slave subclasses to service memory transactions from python 
masters and python Slave subclasses to receive service memory transactions 
initiated by c++ masters.

See :ref:`interfaces_memory_master` for more detail on the Master class.

Below is an example class which will initiate a read followed by a write.

.. code-block:: python

    import pyrogue
    import rogue.interfaces.memory

    # Create a subclass of a memory Master
    # This master will initiate a read from a passed address and
    # increment that value at that address by a passed value
    class MyMemMaster(rogue.interfaces.memory.Master):

        # Init method must call the parent class init
        def __init__(self):
            super().__init__()
 
        # Start a sequence with passed address and increment value
        def incAtAddress(self, address, value):

            # Create byte array for data
            ba = bytearray(4)

            # Clear any existing errors
            self._clearError()

            # Start read transaction from address into bytearray
            # size = 4, byte array offset = 0
            id = self._reqTransaction(address, ba, 4, 0, rogue.interfaces.memory.Read)

            # Wait for transaction to complete
            _waitTransaction(id)

            # Check transaction result
            if self._getError() != "":
                print("got error")
                return False

            # Increment value in byte array by passed value
            oldValue = int.from_bytes(ba, 'little', signed=False)
            oldvalue += value
            ba = oldValue.to_bytes(4, 'little', signed=False)

            # Start write transaction to address from bytearray
            # size = 4, byte array offset = 0
            id = self._reqTransaction(address, ba, 4, 0, rogue.interfaces.memory.Write)

            # Wait for transaction to complete
            self._waitTransaction(id)

            # Check transaction result
            self.if _getError() != "":
                print("got error")
                return False
            else:
                return True

The equivalent code in C++ is show below:

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <rogue/interfaces/memory/Master.h>

   // Create a subclass of a memory Master
   // This master will initiate a read from a passed address and
   // increment that value at that address by a passed value
   class MyMemMaster : public rogue::interfaces::memory::Master {
      public:

         // Create a static class creator to return our custom class
         // wrapped with a shared pointer
         static std::shared_ptr<MyMemMaster> create() {
            static std::shared_ptr<MyMemMaster> ret =
               std::make_shared<MyMemMaster>();
            return(ret);
         }

         // Standard class creator which is called by create 
         MyMemMaster() : rogue::interfaces::memory::Master() {}

         // Start a sequence with passed address and increment value
         bool incAtAddress(uint64_t address, uint32_t value) {
            uint32_t rValue;
            uint32_t id;

            // Clear any existing errors
            this->clearError();

            // Start read transaction, size=4
            id = this->reqTransaction(address, 4, &rValue, rogue::interfaces::memory::Read);

            // Wait for transaction to complete
            this->waitTransaction(id)

            // Check transaction result
            if ( this->getError() != "" ) {
                printf("got error\n");
                return false;
            }

            // Increment value by passed value
            rValue += value;

            // Start write transaction, size = 4
            id = this->reqTransaction(address, 4, &rValue, rogue::interfaces::memory::Write);

            // Wait for transaction to complete
            this->waitTransaction(id)

            // Check transaction result
            if ( this->getError() != "" ) {
                printf("got error\n");
                return false;
            } else return true;

         }
   };

   // Shared pointer alias
   typedef std::shared_ptr<MyMemMaster> MyMemMasterPtr;

Of course neither of the above classes ensure that the memory does not get modified by
another process between the read and write. The pyrogue device management tree manages
this at a higher level.

