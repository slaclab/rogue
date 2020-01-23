.. _interfaces_memory_slave_ex:

====================
Memory Slave Example
====================

Unlike the :ref:`interfaces_memory_master_ex`, it is more common for the user to implement a custom
memory Slave to interface with hardware that uses a proprietary protocol.

Python and C++ subclasses of the Slave class can be used interchangeably, allowing c++ subclasses 
to service memory transactions from python masters and python subclasses to receive service
memory transactions initiated by c++ masters.

In the below example assume there is a a protocol that has the following functions to
initiate a read and write transaction:

* protocolRead(id, address, size)
* protocolWrite(id, address, size, data)

And executes the following callbacks when the transaction completes:

* protocolReadDone(id, data, result)
* protocolWriteDone(id, result)

See the SrpV3 protocol implementation in Rogue for a more detailed example.

See :ref:`interfaces_memory_slave` for more detail on the Slave class.

.. code-block:: python

    import pyrogue
    import rogue.interfaces.memory

    # Create a subclass of a memory Slave
    # Assume our min size = 4 bytes and our max size is 1024 bytes
    class MyMemSlave(rogue.interfaces.memory.Slave):

        # Init method must call the parent class init
        def __init__(self):

            # Here we set min and max size
            super().__init__(4,1024)

        # Entry point for incoming transaction
        def _doTransaction(self,transaction):

            # First we lock the transaction data
            with transaction.lock():

                # Next store the transaction in the local map so we
                # can retrieve it when the protocol returns
                self._addTransaction(transaction)

                # Handle write or post
                if transaction.type() == rogue.interfaces.memory.Write or
                   transaction.type() == rogue.interfaces.memory.Post:

                   # Copy data into byte array
                   data = bytearray(transaction.size())
                   transaction.getData(data,0)

                   # Next forward the transaction data to our protocol
                   protocolWrite(transaction.id(),
                                 transaction.address(),
                                 transaction.size(), data)

                # Handle read or verify read
                else:

                   # Next forward the transaction data to our protocol
                   protocolRead(transaction.id, 
                                transaction.address(),
                                transaction.size())

                # We are done for now until protocol returns below

        # Protocol callback for write complete
        def protocolWriteDone(self,id,result):

            # First attempt to retrieve transaction
            tran = self._getTransaction(id)

            # Transaction is no longer valid
            if tran is None:
                return

            # Lock transaction
            with tran.lock():

                # make sure transaction is not stale
                if tran.expired():
                    return

                # If an error occurred, complete result with bus fail
                if not result:
                    tran.error(f"Got a bad result: {result}")
               
                # Otherwise complete transaction with success 
                else: 
                    tran.done()

        # Protocol callback for read complete
        def protocolReadDone(self,id,data,result):

            # First attempt to retrieve transaction
            tran = self._getTransaction(id)

            # Transaction is no longer valid
            if tran is None:
                return

            # Lock transaction
            with tran.lock():

                # make sure transaction is not stale
                if tran.expired():
                    return

                # If an error occurred, complete result with bus fail
                if not result:
                    tran.error(f"Got a bad result: {result}")
               
                # Otherwise set the read data back to the transaction
                # and complete without error
                else: 
                    tran.setData(data,0)
                    tran.done()

The equivalent code in C++ is show below:

.. code-block:: c

   #include <rogue/interfaces/memory/Constants.h>
   #include <rogue/interfaces/memory/Slave.h>

   // Create a subclass of a memory Slave
   // Assume our min size = 4 bytes and our max size is 1024 bytes
   class MyMemSlave : public rogue::interfaces::memory::Slave {
      public:

         // Create a static class creator to return our custom class
         // wrapped with a shared pointer
         static std::shared_ptr<MyMemSlave> create() {
            static std::shared_ptr<MyMemSlave> ret =
               std::make_shared<MyMemSlave>();
            return(ret);
         }

         // Standard class creator which is called by create 
         // Here we set min and max size
         MyMemSlave() : rogue::interfaces::memory::Slave(4,1024) {}

         // Entry point for incoming transaction
         void doTransaction(rogue::interfaces::memory::TransactionPtr tran) {

            // First we lock the transaction data with a scoped lock
            rogue::interfaces::memory::TransactionLockPtr lock = tran->lock();

            // Next store the transaction in the local map so we
            // can retrieve it when the protocol returns
            this->addTransaction(tran);

            // Handle write or post
            if ( tran->type() == rogue::interfaces::memory::Write ||
                 tran->type() == rogue::interfaces::memory::Post ) {

               // Next forward the transaction data to our protocol
               // Use pointer directly from transaction 
               protocolWrite(tran->id(),
                             tran->address(),
                             tran->size(), tran->begin());

            }

            // Handle read or verify read
            else {

               // Next forward the transaction data to our protocol
               protocolRead(tran->id(),
                            tran->address(),
                            tran->size());
            }

            // We are done for now until protocol returns below

         // Protocol callback for write complete
         void protocolWriteDone(uint32_t id, bool result) {
            rogue::interfaces::memory::TransactionPtr tran;  

            // First attempt to retrieve transaction
            if ( (tran = this->getTransaction(id)) == NULL ) return;

            // Lock the transaction data with a scoped lock
            rogue::interfaces::memory::TransactionLockPtr lock = tran->lock();

            // make sure transaction is not stale
            if ( tran->expired() ) return;

            // If an error occured, complete result with bus fail
            if ( ! result ) tran->error("Got a bad protocol result %i",result);
               
            // Otherwise complete transaction with success 
            else tran->done();
         }

         // Protocol callback for read complete
         void protocolReadDone(uint32_t id, uint8_t *data, bool result) {
            rogue::interfaces::memory::TransactionPtr tran;  

            // First attempt to retrieve transaction
            if ( (tran = this->getTransaction(id)) == NULL ) return;

            // Lock the transaction data with a scoped lock
            rogue::interfaces::memory::TransactionLockPtr lock = tran->lock();

            // make sure transaction is not stale
            if ( tran->expired() ) return;

            // If an error occurred, complete result with bus fail
            if ( ! result ) tran->error("Got a bad protocol result %i",result);
               
            // Otherwise set the read data back to the transaction
            // and complete without error
            else {
               std::copy(data,data+tran->size(),tran->begin());
               tran->done();
            }
         }
   };

   // Shared pointer alias
   typedef std::shared_ptr<MyMemSlave> MyMemSlavePtr;

