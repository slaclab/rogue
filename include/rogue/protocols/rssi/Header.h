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
#include <rogue/interfaces/stream/Frame.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         //! PGP Card class
         class Header {

            public:

               //! Header Size
               static const uint32_t HeaderSize = 8;

            private:
   
               //! Frame pointer
               boost::shared_ptr<rogue::interfaces::stream::Frame> frame_;

            protected:

               //! Set bit value
               void setBit ( uint8_t byte, uint8_t bit, bool value);

               //! Get bit value
               bool getBit ( uint8_t byte, uint8_t bit);

               //! Set 8-bit uint value
               void setUInt8 ( uint8_t byte, uint8_t value);

               //! Get 8-bit uint value
               uint8_t getUInt8 ( uint8_t byte );

               //! Set 16-bit uint value
               void setUInt16 ( uint8_t byte, uint16_t value);

               //! Get 16-bit uint value
               uint16_t getUInt16 ( uint8_t byte );

               //! Set 32-bit uint value
               void setUInt32 ( uint8_t byte, uint32_t value);

               //! Get 32-bit uint value
               uint32_t getUInt32 ( uint8_t byte );

               //! compute checksum
               uint16_t compSum ( );

            public:

               //! Create
               static boost::shared_ptr<rogue::protocols::rssi::Header>
                  create(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Setup class in python
               static void setup_python();

               //! Creator
               Header(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Destructor
               ~Header();

               //! Get Frame
               boost::shared_ptr<rogue::interfaces::stream::Frame> getFrame();

               //! Return required size
               virtual uint32_t minSize();

               //! Get header size
               uint8_t getHeaderSize();

               //! Init header contents
               virtual void init(bool setSize);

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
               uint16_t getAcknowledge();

               //! Set acknowledge number
               void setAcknowledge(uint16_t ack);

               //! Dump message contents
               virtual std::string dump();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::rssi::Header> HeaderPtr;

      }
   }
};

#endif

