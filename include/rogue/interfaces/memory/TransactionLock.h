/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Transaction Lock
 * ----------------------------------------------------------------------------
 * File       : TransactionLock.h
 * Created    : 2018-03-16
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Transaction lock
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
#ifndef __ROGUE_INTERFACES_MEMORY_TRANSACTION_LOCK_H__
#define __ROGUE_INTERFACES_MEMORY_TRANSACTION_LOCK_H__
#include <stdint.h>
#include <thread>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Transaction;

         //! Transaction Lock
         /**
          * The TransactionLock is a container for holding a lock on Transaction data while accessing
          * that data. This lock ensures that Transaction is not destroyed when the Slave is updating
          * its data and result. This object is created by calling Transaction::lock().
          */
         class TransactionLock {

               std::shared_ptr<rogue::interfaces::memory::Transaction> tran_;
               bool locked_;

            public:

               // Class factory which returns a pointer to a TransactionLock (TransactionLockPtr)
               static std::shared_ptr<rogue::interfaces::memory::TransactionLock> create (
                  std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

               // Transaction lock constructor
               TransactionLock(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

               // Setup class for use in python
               static void setup_python();

               // Destroy and release the transaction lock
               ~TransactionLock();

               //! Lock associated Transaction if not locked
               /** Exposed as lock() to Python
                */
               void lock();

               //! UnLock associated transaction if locked
               /** Exposed as unlock() to Python
                */
               void unlock();

               //! Enter method for python, does nothing
               /** This exists only to support the
                * with call in python.
                *
                * Exposed as __enter__() to Python
                */
               void enter();

               //! Exit method for python, does nothing
               /** This exists only to support the
                * with call in python.
                *
                * Exposed as __exit__() to Python
                */
               void exit(void *, void *, void *);
         };

         //! Alias for using shared pointer as TransactionLockPtr
         typedef std::shared_ptr<rogue::interfaces::memory::TransactionLock> TransactionLockPtr;

      }
   }
}

#endif

