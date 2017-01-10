/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Header Class
 * ----------------------------------------------------------------------------
 * File       : Header.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI header
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
#ifndef __ROGUE_PROTOCOLS_RSSI_HEADER_H__
#define __ROGUE_PROTOCOLS_RSSI_HEADER_H__
#include <stdint.h>
#include <boost/shared_ptr.hpp>

namespace rogue {
   namespace protocols {
      namespace rssi {

         //! PGP Card class
         class Header {

            protected:

               //! Pointer to data
               uint8_t * data_;

               //! Header size
               uint32_t size_;

            public:

               //! Class creation
               static boost::shared_ptr<rogue::protocols::rssi::Header> create (uint8_t * data, uint32_t size);

               //! Return required size
               static uint32_t size();

               //! Creator
               Header(uint8_t *data, uint32_t size);

               //! Destructor
               ~Header();

               //! Get header size
               uint8_t getHeaderSize();

               //! Init header contents
               virtual void init();

               //! Verify header checksum
               bool verify();

               //! Update checksum
               void update();

               //! Get syn flag
               bool getSyn();

               //! Set syn flag
               void setSyn(bool state);

               //! Get ack flag
               bool getAck();

               //! Set ack flag
               void setAck(bool state);

               //! Get eack flag
               bool getEAck();

               //! Set eack flag
               void setEAck(bool state);

               //! Get rst flag
               bool getRst();

               //! Set rst flag
               void setRst(bool state);

               //! Get NUL flag
               bool getNul();

               //! Set NUL flag
               void setNul(bool state);

               //! Get Busy flag
               bool getBusy();

               //! Set Busy flag
               void setBusy(bool state);

               //! Get sequence number
               uint16_t getSequence();

               //! Set sequence number
               void setSequence(uint16_t seq);

               //! Get acknowledge number
               uint16_t getAcknowledg();

               //! Set acknowledge number
               void setAcknowledge(uint16_t ack);

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::rssi::Header> HeaderPtr;

      }
   }
};

#endif

