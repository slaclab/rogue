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
 *
 *    May want to have ability to lock block for overall access.
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

#include <boost/python.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         //! Transaction container
         class Block {

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
               uint32_t stale_;

               //! Locking mutex
               boost::mutex mtx_;

            public:

               //! Create a block, class creator
               static boost::shared_ptr<rogue::interfaces::memory::Block> create (
                     uint64_t address, uint32_t size );

               //! Create an block
               Block(uint64_t address, uint32_t size );

               //! Destroy a block
               ~Block();

               //! Get the address
               uint64_t getAddress();

               //! Get the size
               uint32_t getSize();

               //! Get pointer to raw data
               uint8_t * getData();

               //! Get pointer to raw data, python
               boost::python::object getDataPy();

               //! Get error state
               uint32_t getError();

               //! Set error state
               void setError(uint32_t error);

               //! Get stale state
               bool getStale();

               //! Set stale state
               void setStale(bool stale);

               //! Get uint8 at offset
               uint8_t getUInt8(uint32_t offset);

               //! Set uint8 at offset
               void setUInt8(uint32_t offset, uint8_t value);

               //! Get uint32 at offset
               uint32_t getUInt32(uint32_t offset);

               //! Set uint32  offset
               void setUInt32(uint32_t offset, uint32_t value);

               //! Get arbitrary bit field at byte and bit offset
               uint32_t getBits(uint32_t bitOffset, uint32_t bitCount);

               //! Set arbitrary bit field at byte and bit offset
               void setBits(uint32_t bitOffset, uint32_t bitCount, uint32_t value);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::Block> BlockPtr;

      }
   }
}

#endif

