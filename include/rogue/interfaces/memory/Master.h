/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory master interface.
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#ifndef __ROGUE_INTERFACES_MEMORY_MASTER_H__
#define __ROGUE_INTERFACES_MEMORY_MASTER_H__
#include <stdint.h>
#include <vector>
#include <map>
#include <thread>
#include <rogue/Logging.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Slave;
         class Transaction;

         //! Master for a memory transaction interface
         /** The Master class is the initiator for any Memory transactions on a bus. Each
          * master is connected to a single next level Slave or Hub class. Multiple Hub levels
          * are allowed in a memory tree. Each Hub has an offset which will be applied to
          * the memory transaction address as it flows down to the lowest level Slave device.
          */
         class Master {
            friend class Transaction;

            private:

               //! Alias for map
               typedef std::map<uint32_t, std::shared_ptr<rogue::interfaces::memory::Transaction> > TransactionMap;

               //! Transaction map
               TransactionMap tranMap_;

               //! Slave. Used for request forwards.
               std::shared_ptr<rogue::interfaces::memory::Slave> slave_;

               //! Timeout value
               struct timeval sumTime_;

               //! Mutex
               std::mutex mastMtx_;

               //! Error status
               std::string error_;

               //! Log
               std::shared_ptr<rogue::Logging> log_;

            public:

               //! Class factory which returns a pointer to a Master (MasterPtr)
               /** Exposed as rogue.interfaces.memory.Master() to Python
                */
               static std::shared_ptr<rogue::interfaces::memory::Master> create ();

               // Setup class for use in python
               static void setup_python();

               // Create a Master instance
               Master();

               // Destroy the Master
               virtual ~Master();

               //! Stop the interface
               virtual void stop();

               //! Set slave or Hub device
               /** The Master will pass the transaction data to this Slave or Hub device. This
                * slave may be the lowest level Slave or a Hub which forwards transactions
                * on to the lower Slave.
                *
                * Exposed to python as _setSlave()
                * @param slave Slave device pointer SlavePtr
                */
               void setSlave ( std::shared_ptr<rogue::interfaces::memory::Slave> slave );

               //! Get next level Slave or Hub device
               /** Exposed to python as _getSlave()
                * @return Slave device pointer SlavePtr
                */
               std::shared_ptr<rogue::interfaces::memory::Slave> getSlave();

               //! Query the slave ID
               /* Each Slave in the system has a unique 32-bit ID. This
                * request is forward to the lowest level Slave device in
                * the tree which will service the Transaction for this Master. This
                * allows the system to determine which memory Masters shared the
                * same address space.
                *
                * Exposed to python as _reqSlaveId()
                * @return 32-bit Slave ID
                */
               uint32_t reqSlaveId();

               //! Query the slave Name
               /* Each Slave in the system has a unique name. This
                * request is forward to the lowest level Slave device in
                * the tree which will service the Transaction for this Master. This
                * allows the system to determine which memory Masters shared the
                * same address space.
                *
                * Exposed to python as _reqSlaveName()
                * @return Slave Name
                */
               std::string reqSlaveName();

               //! Query the minimum access size in bytes for interface
               /** This function will query the lowest level Slave device to
                * determine the minimum size for a transaction.
                *
                * Exposed to python as _reqMinAccess()
                * @return Minimum transaction size
                */
               uint32_t reqMinAccess();

               //! Query the maximum access size in bytes for interface
               /** This function will query the lowest level Slave device to
                * determine the maximum size for a transaction.
                *
                * Exposed to python as _reqMaxAccess()
                * @return Maximum transaction size
                */
               uint32_t reqMaxAccess();

               //! Query the address of the next layer down
               /** This method will return the relative offset of the next level
                * Slave or Hub this Master is attached to. This does not included the local
                * Master offset.
                *
                * Exposed to python as _reqAddress()
                * @return Address of next layer this Master is attached to
                */
               uint64_t reqAddress();

               //! Get error of last Transaction
               /** This method returns the error value of the last set of transactions initiated
                * by this master.
                *
                * Exposed to python as _getError()
                * @return Error value
                */
               std::string getError();

               //! Clear the error value
               /** This method clears the error value for this master.
                *
                * Exposed to python as _clearError()
                */
               void clearError();

               //! Set timeout value for transactions
               /** Sets the timeout value for future transactions. THis is the amount of time
                * to wait for a transaction to complete.
                *
                * Exposed to python as _setTimeout()
                * @param timeout Timeout value
                */
               void setTimeout(uint64_t timeout);

               //! Start a new transaction
               /** This method generates the creation of a Transaction object which is then forwarded
                * to the lowest level Slave in the memory bus tree. The passed address is relative
                * to the next layer in the memory tree. (local offset). More than one transaction
                * can be pending for this Master.
                *
                * Not exposed to Python (see reqTransactionPy)
                * @param address Relative 64-bit transaction offset address
                * @param size Transaction size in bytes
                * @param data Pointer to data array used for transaction.
                * @param type Transaction type
                * @return 32-bit transaction id
                */
               uint32_t reqTransaction(uint64_t address, uint32_t size, void *data, uint32_t type);

#ifndef NO_PYTHON

               //! Python version of reqTransaction. Takes a byte array instead of a data pointer.
               /** This method generates the creation of a Transaction object which is then forwarded
                * to the lowest level Slave in the memory bus tree. The passed address is relative
                * to the next layer in the memory tree. (local offset). More than one transaction
                * can be pending for this Master.
                *
                * Exposed to Python as _reqTransaction()
                * @param address Relative 64-bit transaction offset address
                * @param p Byte array used for transaction data
                * @param size Transaction size in bytes
                * @param offset Offset within byte array for transaction
                * @param type Transaction type
                * @return 32-bit transaction id
                */
               uint32_t reqTransactionPy(uint64_t address, boost::python::object p, uint32_t size, uint32_t offset, uint32_t type);

#endif

               //! Helper function to optimize bit copies between byte arrays.
               /** This method will copy bits between two byte arrays.
                *
                * Exposed to python as _copyBits
                * @param dst Destination Python byte array
                * @param dstLsb Least significant bit in destination byte array for copy
                * @param src Source Python byte array
                * @param srcLsb Least significant bit in source byte array for copy
                * @param size Number of bits to copy
                */
               static void copyBits(uint8_t *dstData, uint32_t dstLsb, uint8_t *srcData, uint32_t srcLsb, uint32_t size);

#ifndef NO_PYTHON

               // Helper function to optimize bit copies between byte arrays.
               static void copyBitsPy(boost::python::object dst, uint32_t dstLsb, boost::python::object src, uint32_t srcLsb, uint32_t size);

#endif

               //! Helper function to optimize bit setting in a byte array.
               /** This method will set a range of bits in a byte array
                *
                * Exposed to python as _setBits
                * @param dst Destination Python byte array
                * @param lsb Least significant bit in destination byte array for set
                * @param size Number of bits to set
                */
               static void setBits(uint8_t *dstData, uint32_t lsb, uint32_t size);

#ifndef NO_PYTHON

               // Helper function to optimize bit setting in a byte array.
               static void setBitsPy(boost::python::object dst, uint32_t lsb, uint32_t size);

#endif

               //! Helper function to detect bits being set in a byte array.
               /** This method will return true if any bits in a range are set
                *
                * Exposed to python as _anyBits
                * @param src Source Python byte array to check
                * @param lsb Least significant bit in source byte array to check
                * @param size Number of bits to check
                */
               static bool anyBits(uint8_t *srcData, uint32_t lsb, uint32_t size);

#ifndef NO_PYTHON

               // Helper function to detect bits being set in a byte array.
               static bool anyBitsPy(boost::python::object src, uint32_t lsb, uint32_t size);

#endif

#ifndef NO_PYTHON

               //! Support >> operator in python
               void rshiftPy ( boost::python::object p );

#endif

               //! Support >> operator in C++
               std::shared_ptr<rogue::interfaces::memory::Slave> &
                  operator >>(std::shared_ptr<rogue::interfaces::memory::Slave> & other);

            protected:

               //! Internal transaction
               uint32_t intTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> tran);

            public:

               //! Wait for one or more transactions to complete
               /** This method is called to wait on transaction completion or timeout.
                * Passing an id of zero will wait for all current pending transactions to
                * complete.
                *
                * Exposed as _waitTransaction to Python
                * @param id Id of transaction to wait for, 0 to wait for all
                */
               void waitTransaction(uint32_t id);
         };

         //! Alias for using shared pointer as MasterPtr
         typedef std::shared_ptr<rogue::interfaces::memory::Master> MasterPtr;
      }
   }
}

#endif

