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

         class BlockLock;

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

               //! Stale state of memory space
               bool stale_;

               //! Main class mutex
               boost::mutex mtx_;

               //! Transaction is busy
               bool busy_;

               //! Block updated state, set in doneTransaction
               bool updated_;

               //! Current transaction is a write
               bool write_;

               //! Block is enabled for memory access
               bool enable_;

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

               //! Set enable flag
               void setEnable(bool en);

               //! Get enable flag
               bool getEnable();

               //! Get error state without exception
               uint32_t getError();

               //! Get and clear updated state, raise exception if error
               bool getUpdated();

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
               void setTransactionData(void *data, uint32_t offset, uint32_t size);

               //! Get from master to slave, called by slave
               void getTransactionData(void *data, uint32_t offset, uint32_t size);

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

               //////////////////////////////////////
               // Raw access
               //////////////////////////////////////
               
               //! Start raw access. Lock object is returned.
               boost::shared_ptr<rogue::interfaces::memory::BlockLock> lockRaw(bool write);

               //! Get a raw pointer to block data
               uint8_t * rawData (boost::shared_ptr<rogue::interfaces::memory::BlockLock> lock);

               //! Get a raw pointer to block data, python version
               boost::python::object rawDataPy (boost::shared_ptr<rogue::interfaces::memory::BlockLock> lock);

               //! End a raw access. Pass back lock object
               void unlockRaw(boost::shared_ptr<rogue::interfaces::memory::BlockLock> lock);
         };

         //! Hold a lock for raw access
         class BlockLock {
            friend class rogue::interfaces::memory::Block;
            protected:
               bool write_;
               boost::unique_lock<boost::mutex> lock_;
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Block> BlockPtr;
         typedef boost::shared_ptr<rogue::interfaces::memory::BlockLock> BlockLockPtr;

      }
   }
}

#endif

