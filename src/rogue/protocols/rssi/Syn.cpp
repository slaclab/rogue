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

void rpr::Syn::setup_python() {
   // Nothing to do
}

//! Creator
rpr::Syn::Syn(ris::FramePtr frame) : rpr::Header(frame) { }

//! Destructor
rpr::Syn::~Syn() { }

//! Return required size
uint32_t rpr::Syn::minSize() {
   return(SynSize);
}

//! Init header contents
void rpr::Syn::init(bool setSize) {
   rpr::Header::init(setSize);
   setSyn(true);
   setBit(4,4,true);
}

//! Get version field
uint8_t rpr::Syn::getVersion() {
   return(getUInt8(4) >> 4);
}

//! Set version field
void rpr::Syn::setVersion(uint8_t version) {
   uint8_t val;

   val = getUInt8(4);

   val &= 0x0F;
   val |= version << 4;

   setUInt8(4,val);
}

//! Get chk flag
bool rpr::Syn::getChk() {
   return(getBit(4,2));
}

//! Set chk flag
void rpr::Syn::setChk(bool state) {
   setBit(4,2,state);
}

//! Get MAX Outstanding Segments
uint8_t rpr::Syn::getMaxOutstandingSegments() {
   return(getUInt8(5));
}

//! Set MAX Outstanding Segments
void rpr::Syn::setMaxOutstandingSegments(uint8_t max) {
   setUInt8(5,max);
}

//! Get MAX Segment Size
uint16_t rpr::Syn::getMaxSegmentSize() {
   return(getUInt16(6));
}

//! Set MAX Segment Size
void rpr::Syn::setMaxSegmentSize(uint16_t size) {
   setUInt16(6,size);
}

//! Get Retransmission Timeout
uint16_t rpr::Syn::getRetransmissionTimeout() {
   return(getUInt16(8));
}

//! Set Retransmission Timeout
void rpr::Syn::setRetransmissionTimeout(uint16_t to) {
   setUInt16(8,to);
}

//! Get Cumulative Acknowledgement Timeout
uint16_t rpr::Syn::getCumulativeAckTimeout() {
   return(getUInt16(10));
}

//! Set Cumulative Acknowledgement Timeout
void rpr::Syn::setCumulativeAckTimeout(uint16_t to) {
   setUInt16(10,to);
}

//! Get NULL Timeout
uint16_t rpr::Syn::getNullTimeout() {
   return(getUInt16(12));
}

//! Set NULL Timeout
void rpr::Syn::setNullTimeout(uint16_t to) {
   setUInt16(12,to);
}

//! Get Max Retransmissions
uint8_t rpr::Syn::getMaxRetransmissions() {
   return(getUInt8(14));
}

//! Set Max Retransmissions
void rpr::Syn::setMaxRetransmissions(uint8_t max) {
   setUInt8(14,max);
}

//! Get MAX Cumulative Ack
uint8_t rpr::Syn::getMaxCumulativeAck() {
   return(getUInt8(15));
}

//! Set Max Cumulative Ack
void rpr::Syn::setMaxCumulativeAck(uint8_t max) {
   setUInt8(15,max);
}

//! Get Timeout Unit
uint8_t rpr::Syn::getTimeoutUnit() {
   return(getUInt8(17));
}

//! Set Timeout Unit
void rpr::Syn::setTimeoutUnit(uint8_t unit) {
   setUInt8(17,unit);
}

//! Get Connection ID
uint32_t rpr::Syn::getConnectionId() {
   return(getUInt32(18));
}

//! Set Timeout Unit
void rpr::Syn::setConnectionId(uint32_t id) {
   setUInt32(18,id);
}

//! Dump message
std::string rpr::Syn::dump() {
   std::stringstream ret("");
   ret << rpr::Header::dump();

   ret << "      Version : " << std::dec << (uint32_t)getVersion() << std::endl;
   ret << "          Chk : " << std::dec << getChk() << std::endl;
   ret << "  Max Out Seg : " << std::dec << (uint32_t)getMaxOutstandingSegments() << std::endl;
   ret << " Max Seg Size : " << std::dec << (uint32_t)getMaxSegmentSize() << std::endl;
   ret << "  Retran Tout : " << std::dec << (uint32_t)getRetransmissionTimeout() << std::endl;
   ret << " Cum Ack Tout : " << std::dec << (uint32_t)getCumulativeAckTimeout() << std::endl;
   ret << "    Null Tout : " << std::dec << (uint32_t)getNullTimeout() << std::endl;
   ret << "  Max Retrans : " << std::dec << (uint32_t)getMaxRetransmissions() << std::endl;
   ret << "  Max Cum Ack : " << std::dec << (uint32_t)getMaxCumulativeAck() << std::endl;
   ret << " Timeout Unit : " << std::dec << (uint32_t)getTimeoutUnit() << std::endl;
   ret << "      Conn Id : " << std::dec << (uint32_t)getConnectionId() << std::endl;

   return(ret.str());
}

