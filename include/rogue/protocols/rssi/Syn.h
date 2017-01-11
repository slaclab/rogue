/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Syn Class
 * ----------------------------------------------------------------------------
 * File       : Syn.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI SYN frame
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
#ifndef __ROGUE_PROTOCOLS_RSSI_SYN_H__
#define __ROGUE_PROTOCOLS_RSSI_SYN_H__
#include <rogue/protocols/rssi/Header.h>
#include <stdint.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         //! PGP Card class
         class Syn : public rogue::protocols::rssi::Header {

               //! Syn Size
               static const uint32_t SynSize = 24;

            public:

               //! Create
               static boost::shared_ptr<rogue::protocols::rssi::Syn>
                  create(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Return required size
               static uint32_t minSize();

               //! Creator
               Syn(boost::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Destructor
               ~Syn();

               //! Init header contents
               void init();

               //! Get version field
               uint8_t getVersion();

               //! Set version field
               void setVersion(uint8_t version);

               //! Get chk flag
               bool getChk();

               //! Set chk flag
               void setChk(bool state);

               //! Get MAX Outstanding Segments
               uint8_t getMaxOutstandingSegments();

               //! Set MAX Outstanding Segments
               void setMaxOutstandingSegments(uint8_t max);

               //! Get MAX Segment Size
               uint16_t getMaxSegmentSize();

               //! Set MAX Segment Size
               void setMaxSegmentSize(uint16_t size);

               //! Get Retransmission Timeout
               uint16_t getRetransmissionTimeout();

               //! Set Retransmission Timeout
               void setRetransmissionTimeout(uint16_t to);

               //! Get Cumulative Acknowledgement Timeout
               uint16_t getCumulativeAckTimeout();

               //! Set Cumulative Acknowledgement Timeout
               void setCumulativeAckTimeout(uint16_t to);

               //! Get NULL Timeout
               uint16_t getNullTimeout();

               //! Set NULL Timeout
               void setNullTimeout(uint16_t to);

               //! Get Max Retransmissions
               uint8_t getMaxRetransmissions();

               //! Set Max Retransmissions
               void setMaxRetransmissions(uint8_t max);

               //! Get MAX Cumulative Ack
               uint8_t getMaxCumulativeAck();

               //! Set Max Cumulative Ack
               void setMaxCumulativeAck(uint8_t max);

               //! Get Timeout Unit
               uint8_t getTimeoutUnit();

               //! Set Timeout Unit
               void setTimeoutUnit(uint8_t unit);

               //! Get Connection ID
               uint32_t getConnectionId();

               //! Set Timeout Unit
               void setConnectionId(uint32_t id);

               //! Dump message contents
               std::string dump();

         };

         // Convienence
         typedef boost::shared_ptr<rogue::protocols::rssi::Syn> SynPtr;

      }
   }
};

#endif

