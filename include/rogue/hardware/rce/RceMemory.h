/**
 *-----------------------------------------------------------------------------
 * Title      : RCE Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : RceMemory.h
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
#ifndef __ROGUE_HARDWARE_RCE_RCE_MEMORY_H__
#define __ROGUE_HARDWARE_RCE_RCE_MEMORY_H__
#include <rogue/interfaces/memory/Slave.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>

namespace rogue {
   namespace hardware {
      namespace rce {

         //! Memory space tracking
         class RceMemoryMap {
            public:
               uint32_t  base;
               uint32_t  size;
               uint8_t * ptr;
         };

         //! PGP Card class
         class RceMemory : public rogue::interfaces::memory::Slave {

               //! RceMemory file descriptor
               int32_t  fd_;

               //! Tracked mapped spaces
               std::vector<rogue::hardware::rce::RceMemoryMap> maps_;

               //! Lock for vector access
               boost::mutex mapMtx_;

               // Find matching address space, lock before use
               uint8_t * findSpace (uint32_t base, uint32_t size);

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::rce::RceMemory> create ();

               //! Setup class in python
               static void setup_python();

               //! Creator
               RceMemory();

               //! Destructor
               ~RceMemory();

               //! Open the device.
               bool open ();

               //! Close the device
               void close();

               //! Add a memory space
               void addMap(uint32_t address, uint32_t size);

               //! Issue a set of write transactions
               bool doWrite (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);

               //! Issue a set of read transactions
               bool doRead  (boost::shared_ptr<rogue::interfaces::memory::BlockVector> blocks);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::rce::RceMemory> RceMemoryPtr;

      }
   }
};

#endif

