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

               //! Address of memory block
               uint64_t address_;

               //! Size of memory block
               uint32_t size_;

               //! Pointer to data
               uint8_t * data_;

               //! Error state of last transaction
               /*
                * The error field is interface specific
                */
               uint32_t error_;

               //! Stale state of memory space
               bool stale_;

               //! Main class mutex
               boost::mutex mtx_;

               //! Transaction is busy
               bool busy_;

               //! Busy condition
               boost::condition_variable busyCond_;

               //! Internal function to wait for busy = false and acquire lock
               boost::unique_lock<boost::mutex> lockAndCheck(bool errEnable);

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

               //! Set timeout value
               void setTimeout(uint32_t timeout);

               //! Get the address
               uint64_t getAddress();

               //! Adjust the address
               void adjAddress(uint64_t mask, uint64_t addr);

               //! Get the size
               uint32_t getSize();

               //! Get error state
               uint32_t getError();

               //! Get stale state
               bool getStale();

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
               void doneTransaction(uint32_t error);

               //! Set to master from slave, called by slave
               void setData(void *data, uint32_t offset, uint32_t size);

               //! Get from master to slave, called by slave
               void getData(void *data, uint32_t offset, uint32_t size);

               //////////////////////////////////////
               // Access Methods
               //////////////////////////////////////

               //! Get uint8 at offset
               uint8_t getUInt8(uint32_t offset);

               //! Set uint8 at offset
               void setUInt8(uint32_t offset, uint8_t value);

               //! Get uint16 at offset
               uint16_t getUInt16(uint32_t offset);

               //! Set uint16 at offset
               void setUInt16(uint32_t offset, uint16_t value);

               //! Get uint32 at offset
               uint32_t getUInt32(uint32_t offset);

               //! Set uint32  offset
               void setUInt32(uint32_t offset, uint32_t value);

               //! Get uint64 at offset
               uint64_t getUInt64(uint32_t offset);

               //! Set uint64  offset
               void setUInt64(uint32_t offset, uint64_t value);

               //! Get arbitrary bit field at byte and bit offset
               uint32_t getBits(uint32_t bitOffset, uint32_t bitCount);

               //! Set arbitrary bit field at byte and bit offset
               void setBits(uint32_t bitOffset, uint32_t bitCount, uint32_t value);

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

