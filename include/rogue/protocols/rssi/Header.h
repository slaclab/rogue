/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Header Class
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
#include <memory>
#include <rogue/interfaces/stream/Frame.h>

namespace rogue {
   namespace protocols {
      namespace rssi {

         //! PGP Card class
         class Header {

               //! Set 16-bit uint value
               inline void setUInt16 ( uint8_t *data, uint8_t byte, uint16_t value);

               //! Get 16-bit uint value
               inline uint16_t getUInt16 ( uint8_t *data, uint8_t byte );

               //! Set 32-bit uint value
               inline void setUInt32 ( uint8_t *data, uint8_t byte, uint32_t value);

               //! Get 32-bit uint value
               inline uint32_t getUInt32 ( uint8_t *data, uint8_t byte );

               //! compute checksum
               uint16_t compSum (uint8_t *data, uint8_t size);

            public:

               //! Header Size
               static const  int32_t HeaderSize = 8;
               static const uint32_t SynSize    = 24;

            private:

               //! Frame pointer
               std::shared_ptr<rogue::interfaces::stream::Frame> frame_;

               //! Time last transmitted
               struct timeval time_;

               //! Transmit count
               uint32_t count_;

            public:

               //! Create
               static std::shared_ptr<rogue::protocols::rssi::Header>
                  create(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Creator
               Header(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

               //! Destructor
               ~Header();

               //! Get Frame
               std::shared_ptr<rogue::interfaces::stream::Frame> getFrame();

               //! Verify header checksum. Also inits records.
               bool verify();

               //! Update header with settings and update checksum
               void update();

               //! Get time
               struct timeval & getTime();

               //! Get Count
               uint32_t count();

               //! Reset tx time
               void rstTime();

               //! Dump message contents
               std::string dump();

               //! Syn flag
               bool syn;

               //! Ack flag
               bool ack;

               //! Rst flag
               bool rst;

               //! NUL flag
               bool nul;

               //! Busy flag
               bool busy;

               //! Sequence number
               uint8_t sequence;

               //! Acknowledge number
               uint8_t acknowledge;

               //! Version field
               uint8_t version;

               //! Chk flag
               bool chk;

               //! MAX Outstanding Segments
               uint8_t maxOutstandingSegments;

               //! MAX Segment Size
               uint16_t maxSegmentSize;

               //! Retransmission Timeout
               uint16_t retransmissionTimeout;

               //! Cumulative Acknowledgment Timeout
               uint16_t cumulativeAckTimeout;

               //! NULL Timeout
               uint16_t nullTimeout;

               //! Max Retransmissions
               uint8_t maxRetransmissions;

               //! MAX Cumulative Ack
               uint8_t maxCumulativeAck;

               //! Timeout Unit
               uint8_t timeoutUnit;

               //! Connection ID
               uint32_t connectionId;

         };

         // Convienence
         typedef std::shared_ptr<rogue::protocols::rssi::Header> HeaderPtr;

      }
   }
};

#endif

