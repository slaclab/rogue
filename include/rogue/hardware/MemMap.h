/**
 *-----------------------------------------------------------------------------
 * Title      : Raw Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : MemMap.h
 * Created    : 2019-11-18
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
#ifndef __ROGUE_HARDWARE_MEM_MAP_H__
#define __ROGUE_HARDWARE_MEM_MAP_H__
#include <rogue/interfaces/memory/Slave.h>
#include <rogue/interfaces/memory/Transaction.h>
#include <thread>
#include <mutex>
#include <stdint.h>
#include <rogue/Logging.h>
#include <rogue/Queue.h>

#define MAP_DEVICE "/dev/mem"

namespace rogue {
   namespace hardware {

      //! Raw Memory Map Class
      /** This class provides a bridge between the Rogue memory interface and
       * a standard Linux /dev/map interface.
       */
      class MemMap : public rogue::interfaces::memory::Slave {

            //! MemMap file descriptor
            int32_t  fd_;

            //! Size
            uint64_t size_;

            //! Memory Mapped Pointer
            volatile uint8_t * map_;

            // Logging
            std::shared_ptr<rogue::Logging> log_;

            std::thread* thread_;
            bool threadEn_;

            //! Thread background
            void runThread();

            // Queue
            rogue::Queue<std::shared_ptr<rogue::interfaces::memory::Transaction>> queue_;

         public:

            //! Class factory which returns a MemMapPtr to a newly created MemMap object
            /** Exposed to Python as rogue.hardware.MemMap()
             * @param base Base address to map
             * @param size Size of address space to map
             * @return MemMap pointer (MemMapPtr)
             */
            static std::shared_ptr<rogue::hardware::MemMap> create (uint64_t base, uint32_t size);

            // Setup class for use in python
            static void setup_python();

            // Class Creator
            MemMap(uint64_t base, uint32_t size);

            // Destructor
            ~MemMap();

            // stop interface
            void stop();

            // Accept as transaction from the memory Master as defined in the Slave class.
            void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> tran);
      };

      //! Alias for using shared pointer as TcpClientPtr
      typedef std::shared_ptr<rogue::hardware::MemMap> MemMapPtr;

   }
};

#endif

