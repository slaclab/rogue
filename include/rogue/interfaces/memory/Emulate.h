/**
 *-----------------------------------------------------------------------------
 * Title      : Memory slave emulator
 * ----------------------------------------------------------------------------
 * File       : Emulator.h
 * ----------------------------------------------------------------------------
 * Description:
 * A memory space emulator. Allows user to test a Rogue tree without real hardware.
 * This block will auto allocate memory as needed.
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
#ifndef __ROGUE_INTERFACES_MEMORY_EMULATOR_H__
#define __ROGUE_INTERFACES_MEMORY_EMULATOR_H__
#include <stdint.h>
#include <vector>
#include <memory>

#include <rogue/interfaces/memory/Slave.h>
#include <thread>

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#endif

#define MAP_TYPE std::map<uint64_t, uint8_t *>

namespace rogue {
   namespace interfaces {
      namespace memory {

         //! Memory interface Emlator device
         /** This memory will respond to transactions, emilator hardware by responding to read
          * and write transactions.
          */
         class Emulate : public Slave {

               // Map to store 4K address space chunks
               MAP_TYPE memMap_;

               // Lock
               std::mutex mtx_;

            public:

               //! Class factory which returns a pointer to a Emulate (EmulatePtr)
               /** Exposed to Python as rogue.interfaces.memory.Emualte()
                *
                * @param min The min transaction size, 0 if not a virtual memory space root
                * @param min The max transaction size, 0 if not a virtual memory space root
                */
               static std::shared_ptr<rogue::interfaces::memory::Emulate> create (uint32_t min, uint32_t max);

               // Setup class for use in python
               static void setup_python();

               // Create a Emulate device
               Emulate(uint32_t min, uint32_t max);

               // Destroy the Emulate
               ~Emulate();

               //! Handle the incoming memory transaction
               void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);
         };

         //! Alias for using shared pointer as EmulatePtr
         typedef std::shared_ptr<rogue::interfaces::memory::Emulate> EmulatePtr;
      }
   }
}

#endif

