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
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Transaction;

         //! Transaction
         class TransactionLock {

               boost::shared_ptr<rogue::interfaces::memory::Transaction> tran_;
               bool locked_;

            public:

               //! Create a transaction container
               static boost::shared_ptr<rogue::interfaces::memory::TransactionLock> create (
                  boost::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

               //! Constructor
               TransactionLock(boost::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

               //! Setup class in python
               static void setup_python();

               //! Destructor
               ~TransactionLock();

               //! lock
               void lock();

               //! lock
               void unlock();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::TransactionLock> TransactionLockPtr;

      }
   }
}

#endif

