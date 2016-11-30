/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Block
 * ----------------------------------------------------------------------------
 * File       : Block.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Memory block container. Used to issue read and write transactions 
 * to a memory interface. 
 * TODO
 *    Consider endian issues.
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
#ifndef __ROGUE_INTERFACES_MEMORY_BLOCK_H__
#define __ROGUE_INTERFACES_MEMORY_BLOCK_H__
#include <stdint.h>
#include <vector>

#include <rogue/interfaces/memory/Master.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         //! Transaction container
         class Block : public Master {

               //! Transaction timeout
               uint32_t timeout_;

               //! Pointer to data
               uint8_t * data_;

               //! Error state of last transaction
               /*
                * The error field is interface specific
                */
               uint32_t error_;

               //! Main class mutex
               boost::mutex mtx_;

               //! Transaction is busy
               bool busy_;

               //! Block updated state
               bool updated_;

               //! Current transaction is a write
               bool write_;

               //! Block is enabled for memory access
               bool enable_;

               //! Address
               uint64_t address_;

               //! Size 
               uint32_t size_;

               //! Busy condition
               boost::condition_variable busyCond_;

               //! Internal function to wait for busy = false and lock
               boost::unique_lock<boost::mutex> waitAndLock();

            public:

               //! Create a block, class creator
               static boost::shared_ptr<rogue::interfaces::memory::Block> create (
                     uint64_t address, uint32_t size );

               //! Setup class in python
               static void setup_python();

               //! Create an block
               Block(uint64_t address, uint32_t size );

               //! Destroy a block
               ~Block();

               //! set address
               void setAddress(uint64_t address);

               //! Get address
               uint64_t getAddress();

               //! Set size
               void setSize(uint32_t size);

               //! Get size
               uint32_t getSize();

               //! Set timeout value
               void setTimeout(uint32_t timeout);

               //! Set enable flag
               void setEnable(bool en);

               //! Get enable flag
               bool getEnable();

               //! Get error state without generating exception
               /*
                * Error state is not cleared until another transaction
                * is generated.
                */
               uint32_t getError();

               //! Get and clear updated state, raise exception if error
               /*
                * Get updated will return true if the most recent
                * tranasaction was a read. This allows the upper
                * level to check all memory blocks to determine 
                * which ones were updated. Doing this at this level
                * takes advantage of the locking which exists in this
                * module.
                */
               bool getUpdated();

               //////////////////////////////////////
               // Transaction Methods
               //////////////////////////////////////

               //! Generate background read transaction
               void backgroundRead();
               
               //! Generate blocking read transaction
               void blockingRead();
               
               //! Generate background write transaction
               void backgroundWrite();
               
               //! Generate blocking write transaction
               void blockingWrite();
               
               //! Generate posted write transaction
               void postedWrite();

               //////////////////////////////////////
               // Slave Interface Transactions
               //////////////////////////////////////

               //! Post a transaction, called locally, forwarded to slave
               void reqTransaction(bool write, bool posted);

               //! Transaction complete, set by slave
               void doneTransaction(uint32_t id, uint32_t error);

               //////////////////////////////////////
               // Access Methods
               //////////////////////////////////////

               //! Get arbitrary bit field at bit offset
               uint64_t getUInt(uint32_t bitOffset, uint32_t bitCount);

               //! Set arbitrary bit field at bit offset
               void setUInt(uint32_t bitOffset, uint32_t bitCount, uint64_t value);

               //! Get string
               std::string getString();

               //! Set string
               void setString(std::string value);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Block> BlockPtr;

      }
   }
}

#endif

