/**
 *-----------------------------------------------------------------------------
 * Title      : RSII Syn Class
 * ----------------------------------------------------------------------------
 * File       : Syn.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Syn
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
#include <rogue/protocols/rssi/Syn.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>
#include <stdint.h>
#include <rogue/interfaces/stream/Buffer.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Create
rpr::SynPtr rpr::Syn::create(ris::FramePtr frame) {
   rpr::SynPtr r = boost::make_shared<rpr::Syn>(frame);
   return(r);
}

//! Return required size
uint32_t rpr::Syn::minSize() {
   return(SynSize);
}

//! Creator
rpr::Syn::Syn(ris::FramePtr frame) : rpr::Header(frame) { }

//! Destructor
rpr::Syn::~Syn() { }

//! Init header contents
void rpr::Syn::init() {
   memset(frame_->getBuffer(0)->getRawData(),0,SynSize);
   frame_->getBuffer(0)->getRawData()[0] = SynSize;
   frame_->getBuffer(0)->getRawData()[1] = 0x80;
   frame_->getBuffer(0)->getRawData()[5] = 0x08;
}

//! Get version field
uint8_t rpr::Syn::getVersion() {
   return((frame_->getBuffer(0)->getRawData()[5] >> 4) & 0xF);
}

//! Set version field
void rpr::Syn::setVersion(uint8_t version) {
   frame_->getBuffer(0)->getRawData()[5] &= 0xF;
   frame_->getBuffer(0)->getRawData()[5] |= (version << 4);
}

//! Get chk flag
bool rpr::Syn::getChk() {
   return(frame_->getBuffer(0)->getRawData()[5] & 0x04);
}

//! Set chk flag
void rpr::Syn::setChk(bool state) {
   frame_->getBuffer(0)->getRawData()[5] &= 0x0B;
   if ( state ) frame_->getBuffer(0)->getRawData()[5] |= 0x04;
}

//! Get MAX Outstanding Segments
uint8_t rpr::Syn::getMaxOutstandingSegments() {
   return(frame_->getBuffer(0)->getRawData()[4]);
}

//! Set MAX Outstanding Segments
void rpr::Syn::setMaxOutstandingSegments(uint8_t max) {
   frame_->getBuffer(0)->getRawData()[4] = max;
}

//! Get MAX Segment Size
uint16_t rpr::Syn::getMaxSegmentSize() {
   uint16_t * val = (uint16_t *)&(frame_->getBuffer(0)->getRawData()[6]);
   return(le16toh(*val));
}

//! Set MAX Segment Size
void rpr::Syn::setMaxSegmentSize(uint16_t size) {
   uint16_t * val = (uint16_t *)&(frame_->getBuffer(0)->getRawData()[6]);
   *val = htole16(size);
}

//! Get Retransmission Timeout
uint16_t rpr::Syn::getRetransmissionTimeout() {
   uint16_t * val = (uint16_t *)&(frame_->getBuffer(0)->getRawData()[8]);
   return(le16toh(*val));
}

//! Set Retransmission Timeout
void rpr::Syn::setRetransmissionTimeout(uint16_t to) {
   uint16_t * val = (uint16_t *)&(frame_->getBuffer(0)->getRawData()[8]);
   *val = htole16(to);
}

//! Get Cumulative Acknowledgement Timeout
uint16_t rpr::Syn::getCumulativeAckTimeout() {
   uint16_t * val = (uint16_t *)&(frame_->getBuffer(0)->getRawData()[10]);
   return(le16toh(*val));
}

//! Set Cumulative Acknowledgement Timeout
void rpr::Syn::setCumulativeAckTimeout(uint16_t to) {
   uint16_t * val = (uint16_t *)&(frame_->getBuffer(0)->getRawData()[10]);
   *val = htole16(to);
}

//! Get NULL Timeout
uint16_t rpr::Syn::getNullTimeout() {
   uint16_t * val = (uint16_t *)&(frame_->getBuffer(0)->getRawData()[12]);
   return(le16toh(*val));
}

//! Set NULL Timeout
void rpr::Syn::setNullTimeout(uint16_t to) {
   uint16_t * val = (uint16_t *)&(frame_->getBuffer(0)->getRawData()[12]);
   *val = htole16(to);
}

//! Get Max Retransmissions
uint8_t rpr::Syn::getMaxRetransmissions() {
   return(frame_->getBuffer(0)->getRawData()[15]);
}

//! Set Max Retransmissions
void rpr::Syn::setMaxRetransmissions(uint8_t max) {
   frame_->getBuffer(0)->getRawData()[15] = max;
}

//! Get MAX Cumulative Ack
uint8_t rpr::Syn::getMaxCumulativeAck() {
   return(frame_->getBuffer(0)->getRawData()[14]);
}

//! Set Max Cumulative Ack
void rpr::Syn::setMaxCumulativeAck(uint8_t max) {
   frame_->getBuffer(0)->getRawData()[14] = max;
}

//! Get Timeout Unit
uint8_t rpr::Syn::getTimeoutUnit() {
   return(frame_->getBuffer(0)->getRawData()[16]);
}

//! Set Timeout Unit
void rpr::Syn::setTimeoutUnit(uint8_t unit) {
   frame_->getBuffer(0)->getRawData()[16] = unit;
}

//! Get Connection ID
uint32_t rpr::Syn::getConnectionId() {
   uint32_t * val = (uint32_t *)&(frame_->getBuffer(0)->getRawData()[18]);
   return(le32toh(*val));
}

//! Set Timeout Unit
void rpr::Syn::setConnectionId(uint32_t id) {
   uint32_t * val = (uint32_t *)&(frame_->getBuffer(0)->getRawData()[18]);
   *val = htole32(id);
}

//! Dump message
std::string rpr::Syn::dump() {
   std::stringstream ret("");
   ret << rpr::Header::dump();

   ret << "      Version : " << std::dec << getVersion() << std::endl;
   ret << "          Chk : " << std::dec << getChk() << std::endl;
   ret << "  Max Out Seg : " << std::dec << getMaxOutstandingSegments() << std::endl;
   ret << " Max Seg Size : " << std::dec << getMaxSegmentSize() << std::endl;
   ret << "  Retran Tout : " << std::dec << getRetransmissionTimeout() << std::endl;
   ret << " Cum Ack Tout : " << std::dec << getCumulativeAckTimeout() << std::endl;
   ret << "    Null Tout : " << std::dec << getNullTimeout() << std::endl;
   ret << "  Max Retrans : " << std::dec << getMaxRetransmissions() << std::endl;
   ret << "  Max Cum Ack : " << std::dec << getMaxCumulativeAck() << std::endl;
   ret << " Timeout Unit : " << std::dec << getTimeoutUnit() << std::endl;
   ret << "      Conn Id : " << std::dec << getConnectionId() << std::endl;

   return(ret.str());
}

