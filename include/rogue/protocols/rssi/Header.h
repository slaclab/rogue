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
               static const uint32_t SynSize    = 24;

            private:
   
               //! Frame pointer
               boost::shared_ptr<rogue::interfaces::stream::Frame> frame_;

               //! Time last transmitted
               struct timeval time_;

               //! Transmit count
               uint32_t count_;

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

               //! Init header contents for TX
               void txInit(bool syn, bool setSize);

               //! Get Frame
               boost::shared_ptr<rogue::interfaces::stream::Frame> getFrame();

               //! Get header size
               uint8_t getHeaderSize();

               //! Verify header checksum
               bool verify();

               //! Update checksum, tx time and tx count
               void update();

               //! Get time
               struct timeval * getTime();

               //! Get Count
               uint32_t count();

               //! Reset tx time
               void rstTime();

               //! Get syn flag
               bool getSyn();

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
               uint8_t getSequence();

               //! Set sequence number
               void setSequence(uint8_t seq);

               //! Get acknowledge number
               uint8_t getAcknowledge();

               //! Set acknowledge number
               void setAcknowledge(uint8_t ack);

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
         typedef boost::shared_ptr<rogue::protocols::rssi::Header> HeaderPtr;

      }
   }
};

#endif

