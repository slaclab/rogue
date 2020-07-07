/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Transaction
 * ----------------------------------------------------------------------------
 * File       : Transaction.h
 * Created    : 2019-03-08
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Transaction
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
#ifndef __ROGUE_INTERFACES_MEMORY_TRANSACTION_H__
#define __ROGUE_INTERFACES_MEMORY_TRANSACTION_H__
#include <memory>
#include <stdint.h>
#include <vector>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <rogue/EnableSharedFromThis.h>
#include <rogue/Logging.h>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

namespace rogue {
   namespace interfaces {
      namespace memory {

         class TransactionLock;
         class Master;
         class Hub;

         //! Transaction Container
         /** The Transaction is passed between the Master and Slave to initiate a transaction.
          * The Transaction class contains information about the transaction as well as the
          * transaction data pointer. Each created transaction object has a unique 32-bit
          * transaction ID which is used to track the transaction. Transactions are never
          * created directly, instead they are created in the Master() class.
          */
         class Transaction : public rogue::EnableSharedFromThis<rogue::interfaces::memory::Transaction> {
            friend class TransactionLock;
            friend class Master;
            friend class Hub;

            public:

               //! Alias for using uint8_t * as Transaction::iterator
               typedef uint8_t * iterator;

            private:

               // Class instance counter
               static uint32_t classIdx_;

               // Class instance lock
               static std::mutex classMtx_;

               // Conditional
               std::condition_variable cond_;

            protected:

               // Transaction timeout
               struct timeval timeout_;

               // Transaction end time
               struct timeval endTime_;

               // Transaction start time
               struct timeval startTime_;

               // Transaction warn time
               struct timeval warnTime_;

#ifndef NO_PYTHON
               // Transaction python buffer
               Py_buffer pyBuf_;
#endif

               // Python buffer is valid
               bool pyValid_;

               // Iterator (mapped to uint8_t * for now)
               iterator iter_;

               // Transaction address
               uint64_t address_;

               // Transaction size
               uint32_t size_;

               // Transaction type
               uint32_t type_;

               // Transaction error
               std::string error_;

               // Transaction id
               uint32_t id_;

               // Done state
               bool done_;

               // Transaction lock
               std::mutex lock_;

               //! Log
               std::shared_ptr<rogue::Logging> log_;

               // Create a transaction container and return a TransactionPtr, called by Master
               static std::shared_ptr<rogue::interfaces::memory::Transaction> create (struct timeval timeout);

               // Wait for the transaction to complete, called by Master
               std::string wait();

            public:

               // Setup class for use in python
               static void setup_python();

               // Create a Transaction. Do not call directly. Only called from the Master class.
               Transaction(struct timeval timeout);

               // Destroy the Transaction.
               ~Transaction();

               //! Lock Transaction and return a TransactionLockPtr object
               /** Exposed as lock() to Python
                *  @return TransactionLock pointer (TransactonLockPtr)
                */
               std::shared_ptr<rogue::interfaces::memory::TransactionLock> lock();

               //! Get expired flag
               /** The expired flag is set by the Master when the Transaction times out
                * and the Master is no longer waiting for the Transaction to complete.
                * Lock must be held before checking the expired status.
                *
                * Exposed as expired() to Python
                * @return True if transaction is expired.
                */
               bool expired();

               //! Get 32-bit Transaction ID
               /** Exposed as id() to Python
                * @return 32-bit transaction ID
                */
               uint32_t id();

               //! Get Transaction address
               /** Exposed as address() to Python
                * @return 64-bit Transaction ID
                */
               uint64_t address();

               //! Get Transaction size
               /** Exposed as size() to Python
                * @return 32-bit Transaction size
                */
               uint32_t size();

               //! Get Transaction type
               /** The transaction type values are defined in Constants
                * Exposed as type() to Python
                * @return 32-bit Transaction type
                */
               uint32_t type();

               //! Refresh transaction timer
               /** Called to refresh the Transaction timer. If the passed reference
                * Transaction is NULL or the Transaction start time is later than the
                * reference transaction, the Transaction timer will be refreshed.
                *
                * Not exposed to Python
                * @param reference Reference TransactionPtr
                */
               void refreshTimer(std::shared_ptr<rogue::interfaces::memory::Transaction> reference);

               //! Complete transaction without error
               /** Lock must be held before calling this method. The
                * error types are defined in Constants.
                *
                * Exposed as done() to Python
                */
               void done();

               //! Complete transaction with passed error, python interface
               /** Lock must be held before calling this method.
                *
                * Exposed as error() to Python
                * @param error Transaction error message
                */
               void errorPy(std::string error);

               //! Complete transaction with passed error
               /** Lock must be held before calling this method.
                *
                * @param error Transaction error message
                */
               void error(const char * fmt, ...);

               //! Get start iterator for Transaction data
               /** Not exposed to Python
                *
                * Lock must be held before calling this method and while
                * updating Transaction data.
                * @return Data iterator as Transaction::iterator
                */
               uint8_t * begin();

               //! Get end iterator for Transaction data
               /** Not exposed to Python
                *
                * Lock must be held before calling this method and while
                * updating Transaction data.
                * @return Data iterator as Transaction::iterator
                */
               uint8_t * end();

#ifndef NO_PYTHON

               //! Method for copying transaction data to Python byte array
               /** Exposed to Python as getData()
                *
                * The size of the data to be copied is defined by the size of
                * the passed data buffer.
                * @param p Python byte array object
                * @param offset Offset for Transaction data access.
                */
               void getData ( boost::python::object p, uint32_t offset );

               //! Method for copying transaction data from Python byte array
               /** Exposed to Python as setData()
                *
                * The size of the data to be copied is defined by the size of
                * the passed data buffer.
                * @param p Python byte array object
                * @param offset Offset for Transaction data access.
                */
               void setData ( boost::python::object p, uint32_t offset );
#endif
         };

         //! Alias for using shared pointer as TransactionPtr
         typedef std::shared_ptr<rogue::interfaces::memory::Transaction> TransactionPtr;

      }
   }
}

#endif

