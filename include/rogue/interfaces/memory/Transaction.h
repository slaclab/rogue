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
#include <boost/enable_shared_from_this.hpp>
#include <stdint.h>
#include <vector>
#include <boost/python.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class TransactionLock;
         class Master;
         class Hub;

         //! Transaction
         class Transaction : public boost::enable_shared_from_this<rogue::interfaces::memory::Transaction> {
            friend class TransactionLock;
            friend class Master;
            friend class Hub;

            public: 
               typedef uint8_t * iterator;
            private:

               //! Class instance counter
               static uint32_t classIdx_;

               //! Class instance lock
               static boost::mutex classMtx_;

               //! Conditional
               boost::condition_variable cond_;

            protected:

               //! Transaction start time
               struct timeval endTime_;

               //! Transaction start time
               struct timeval startTime_;

               //! Transaction python buffer
               Py_buffer pyBuf_;

               //! Python buffer is valid
               bool pyValid_;

               //! Iterator (mapped to uint8_t * for now)
               iterator iter_;

               //! Transaction address
               uint64_t address_;

               //! Transaction size
               uint32_t size_;

               //! Transaction type
               uint32_t type_;

               //! Transaction error
               uint32_t error_;

               //! Transaction id
               uint32_t id_;

               //! Done state
               bool done_;

               //! Transaction lock
               boost::mutex lock_;

            public:

               //! Create a transaction container
               static boost::shared_ptr<rogue::interfaces::memory::Transaction> create ();

               //! Setup class in python
               static void setup_python();

               //! Constructor
               Transaction();

               //! Destructor
               ~Transaction();

               //! Get lock
               boost::shared_ptr<rogue::interfaces::memory::TransactionLock> lock();

               //! Get expired flag
               bool expired();

               //! Get id
               uint32_t id();

               //! Get address
               uint64_t address();

               //! Get size
               uint32_t size();

               //! Get type
               uint32_t type();

               //! Complete transaction with passed error
               void done(uint32_t error);

               //! Wait for the transaction to complete
               uint32_t wait();

               //! start iterator, caller must lock around access
               rogue::interfaces::memory::Transaction::iterator begin();

               //! end iterator, caller must lock around access
               rogue::interfaces::memory::Transaction::iterator end();

               //! Get transaction data from python
               void getData ( boost::python::object p, uint32_t offset );

               //! Set transaction data from python
               void setData ( boost::python::object p, uint32_t offset );
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Transaction> TransactionPtr;

      }
   }
}

#endif

