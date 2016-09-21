/**
 *-----------------------------------------------------------------------------
 * Title      : Memory Block Vector
 * ----------------------------------------------------------------------------
 * File       : BlockVector.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-20
 * Last update: 2016-09-20
 * ----------------------------------------------------------------------------
 * Description:
 * Vector of memory blocks. Wrapper for easy python use.
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
#ifndef __ROGUE_INTERFACES_MEMORY_BLOCK_VECTOR_H__
#define __ROGUE_INTERFACES_MEMORY_BLOCK_VECTOR_H__
#include <stdint.h>
#include <vector>

#include <boost/python.hpp>
#include <boost/thread.hpp>

namespace rogue {
   namespace interfaces {
      namespace memory {

         class Block;

         //! Transaction container
         class BlockVector {

               //! Vector of blocks
               std::vector<boost::shared_ptr<rogue::interfaces::memory::Block>> blocks_;

               //! Lock
               boost::mutex mtx_;

            public:

               //! Create a block vector, class creator
               static boost::shared_ptr<rogue::interfaces::memory::BlockVector> create ();

               //! Create an block vector
               BlockVector();

               //! Destroy a block vector
               ~BlockVector();

               //! Clear the vector
               void clear();

               //! Append a block
               void append(boost::shared_ptr<rogue::interfaces::memory::Block> block);

               //! Get count
               uint32_t count();

               //! Get block at index
               boost::shared_ptr<rogue::interfaces::memory::Block> getBlock(uint32_t idx);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::interfaces::memory::BlockVector> BlockVectorPtr;

      }
   }
}

#endif

