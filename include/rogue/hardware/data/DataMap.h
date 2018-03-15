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

               // Logging
               rogue::LoggingPtr log_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::hardware::data::DataMap> create (std::string path);

               //! Setup class in python
               static void setup_python();

               //! Creator
               DataMap(std::string path);

               //! Destructor
               ~DataMap();

               //! Post a transaction
               void doTransaction(boost::shared_ptr<rogue::interfaces::memory::Transaction> tran);
         };

         // Convienence
         typedef boost::shared_ptr<rogue::hardware::data::DataMap> DataMapPtr;

      }
   }
};

#endif

