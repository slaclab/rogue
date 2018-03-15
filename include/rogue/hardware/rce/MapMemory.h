/**
 *-----------------------------------------------------------------------------
 * Title      : RCE Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : MapMemory.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to RCE mapped memory space.
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
#ifndef __ROGUE_HARDWARE_RCE_MAP_MEMORY_H__
#define __ROGUE_HARDWARE_RCE_MAP_MEMORY_H__
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace hardware {
      namespace rce {

         //! Memory space tracking
         class Map {
            public:
               uint32_t  base;
               uint32_t  size;
               uint8_t * ptr;
         };

         //! PGP Card class
         class MapMemory : public rogue::interfaces::memory::Slave {

               //! MapMemory file descriptor
               int32_t  fd_;

               //! Tracked mapped spaces
               std::vector<rogue::hardware::rce::Map> maps_;

               //! Lock for vector access
               boost::mutex mapMtx_;

               // Find matching address space
               uint8_t * findSpace (uint32_t base, uint32_t size);

               // Logging
               rogue::LoggingPtr log_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::rce::MapMemory> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               MapMemory();

               //! Destructor
               ~MapMemory();

               //! Add a memory space
               void addMap(uint32_t address, uint32_t size);

               //! Post a transaction
               void doTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> tran);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::rce::MapMemory> MapMemoryPtr;

      }
   }
};

#endif

