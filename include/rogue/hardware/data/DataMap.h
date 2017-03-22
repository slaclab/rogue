/**
 *-----------------------------------------------------------------------------
 * Title      : Data Card Memory Mapped Access
 * ----------------------------------------------------------------------------
 * File       : DataMap.h
 * Created    : 2017-03-21
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to data card mapped memory space.
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
#ifndef __ROGUE_HARDWARE_DATA_DATA_MAP_H__
#define __ROGUE_HARDWARE_DATA_DATA_MAP_H__
#include <rogue/interfaces/memory/Slave.h>
#include <boost/python.hpp>
#include <boost/thread.hpp>
#include <stdint.h>
#include <rogue/Logging.h>

namespace rogue {
   namespace hardware {
      namespace data {

         //! PGP Card class
         class DataMap : public rogue::interfaces::memory::Slave {

               //! DataMap file descriptor
               int32_t  fd_;

               //! Tracked mapped spaces
               std::vector<rogue::hardware::rce::Map> maps_;

               //! Lock for vector access
               boost::mutex mapMtx_;

               // Find matching address space
               uint8_t * findSpace (uint32_t base, uint32_t size);

               // Logging
               rogue::Logging * log_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::rce::DataMap> create (std::string path);

               //! Setup class in python
               static void setup_python();

               //! Creator
               DataMap(std::string path);

               //! Destructor
               ~DataMap();

               //! Post a transaction
               void doTransaction(uint32_t id, boost::shared_ptr<rogue::interfaces::memory::Master> master, 
                                  uint64_t address, uint32_t size, uint32_t type);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::rce::DataMap> DataMapPtr;

      }
   }
};

#endif

