/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Data Class
 * ----------------------------------------------------------------------------
 * File       : Data.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI data frame
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
#ifndef __ROGUE_PROTOCOLS_RSSI_DATA_H__
#define __ROGUE_PROTOCOLS_RSSI_DATA_H__
#include <rogue/protocols/rssi/Header.h>
#include <boost/python.hpp>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         //! PGP Card class
         class Data : public rogue::protocols::rssi::Header {

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::rssi::Data> create (uint8_t * data, uint32_t size);

               //! Setup class in python
               static void setup_python();

               //! Return required size
               static uint32_t size(uint32_t dataSize);

               //! Creator
               Data(uint8_t *data, uint32_t size);

               //! Destructor
               ~Data();

               //! Return pointer to data
               uint8_t * getData();

               //! Get data size
               uint32_t getDataSize();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::rssi::Data> DataPtr;

      }
   }
};

#endif

