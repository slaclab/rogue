/**
 *-----------------------------------------------------------------------------
 * Title      : RSII Header Class
 * ----------------------------------------------------------------------------
 * File       : Header.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Header
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
#include <rogue/protocols/rssi/Header.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>
#include <stdint.h>
#include <iomanip>
#include <rogue/interfaces/stream/Buffer.h>
#include <arpa/inet.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Set bit value
void rpr::Header::setBit ( uint8_t byte, uint8_t bit, bool value) {
   if ( bit > 7 )
      throw(rogue::GeneralError::boundary("Header::setBit",bit,7));

   if ( byte >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::setBit",byte,getHeaderSize()));

   frame_->getBuffer(0)->getPayloadData()[byte] &= (0xFF ^ (1 << bit));

   if ( value ) frame_->getBuffer(0)->getPayloadData()[byte] |= (1 << bit);
}

//! Get bit value
bool rpr::Header::getBit ( uint8_t byte, uint8_t bit) {
   if ( bit > 7 )
      throw(rogue::GeneralError::boundary("Header::getBit",bit,7));

   if ( byte >= getHeaderSize() ) 
      throw(rogue::GeneralError::boundary("Header::getBit",byte,getHeaderSize()-1));

   return(((frame_->getBuffer(0)->getPayloadData()[byte] >> bit) & 0x1) != 0);
}

//! Set 8-bit uint value
void rpr::Header::setUInt8 ( uint8_t byte, uint8_t value) {
   if ( byte >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::setUInt8",byte,getHeaderSize()));

   frame_->getBuffer(0)->getPayloadData()[byte] = value;
}

//! Get 8-bit uint value
uint8_t rpr::Header::getUInt8 ( uint8_t byte ) {
   if ( byte >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::getUInt8",byte,getHeaderSize()));

   return(frame_->getBuffer(0)->getPayloadData()[byte]);
}

//! Set 16-bit uint value
void rpr::Header::setUInt16 ( uint8_t byte, uint16_t value) {
   if ( (byte+1) >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::setUInt16",byte+1,getHeaderSize()));

   *((uint16_t *)(&(frame_->getBuffer(0)->getPayloadData()[byte]))) = htons(value);
}

//! Get 16-bit uint value
uint16_t rpr::Header::getUInt16 ( uint8_t byte ) {
   if ( (byte+1) >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::getUInt16",byte+1,getHeaderSize()));

   return(ntohs(*((uint16_t *)(&(frame_->getBuffer(0)->getPayloadData()[byte])))));
}

//! Set 32-bit uint value
void rpr::Header::setUInt32 ( uint8_t byte, uint32_t value) {
   if ( (byte+3) >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::setUInt32",byte+3,getHeaderSize()));

   *((uint32_t *)(&(frame_->getBuffer(0)->getPayloadData()[byte]))) = htonl(value);
}

//! Get 32-bit uint value
uint32_t rpr::Header::getUInt32 ( uint8_t byte ) {
   if ( (byte+3) >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::getUInt32",byte+3,getHeaderSize()));

   return(ntohl(*((uint32_t *)(&(frame_->getBuffer(0)->getPayloadData()[byte])))));
}

//! compute checksum
uint16_t rpr::Header::compSum ( ) {
   int32_t    x;
   uint32_t   sum;

   sum = 0;
   for (x=0; x < getHeaderSize()-2; x = x+2) sum += getUInt16(x);

   sum = (sum % 0x10000) + (sum / 0x10000);
   sum = sum ^ 0xFFFF;
   return(sum);
}

//! Create
rpr::HeaderPtr rpr::Header::create(ris::FramePtr frame) {
   rpr::HeaderPtr r = boost::make_shared<rpr::Header>(frame);
   return(r);
}

void rpr::Header::setup_python() {
   // Nothing to do
}

//! Creator
rpr::Header::Header(ris::FramePtr frame) {
   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("Header::Header","Frame must not be empty!"));
   frame_ = frame;

   gettimeofday(&time_,NULL);
   count_ = 0;
}

//! Destructor
rpr::Header::~Header() { }

//! Init header contents
void rpr::Header::txInit(bool syn, bool setSize) {
   uint32_t headSize = syn?SynSize:HeaderSize;

   if ( frame_->getBuffer(0)->getRawPayload() < headSize )
      throw(rogue::GeneralError::boundary("Header::init",headSize,frame_->getBuffer(0)->getRawPayload()));

   memset(frame_->getBuffer(0)->getPayloadData(),0,headSize);
   frame_->getBuffer(0)->getPayloadData()[1] = headSize;

   if ( setSize ) frame_->getBuffer(0)->setPayload(headSize);

   // Set syn bit
   if ( syn ) {
      setBit(0,7,true); // Syn
      setBit(4,4,true);
   }
}

//! Get Frame
ris::FramePtr rpr::Header::getFrame() {
   return(frame_);
}

//! Get header size
uint8_t rpr::Header::getHeaderSize() {
   uint8_t size = frame_->getBuffer(0)->getPayloadData()[1];

   if ( frame_->getBuffer(0)->getRawPayload() < size )
      throw(rogue::GeneralError::boundary("Header::getHeaderSize",size,frame_->getBuffer(0)->getRawPayload()));

   return(size);
}

//! Verify header contents
bool rpr::Header::verify() {
   if ( frame_->getBuffer(0)->getPayload() < HeaderSize ) return(false);

   uint32_t headSize = getSyn()?SynSize:HeaderSize;

   return( (getHeaderSize() == headSize) && 
           (frame_->getBuffer(0)->getPayload() >= headSize) &&
           (getUInt16(getHeaderSize()-2) == compSum()));
}

//! Update checksum, set tx time and increment tx count
void rpr::Header::update() {
   setUInt16(getHeaderSize()-2,compSum());

   gettimeofday(&time_,NULL);
   count_++;
}

//! Get time
struct timeval * rpr::Header::getTime() {
   return(&time_);
}

//! Get Count
uint32_t rpr::Header::count() {
   return(count_);
}

//! Reset timer
void rpr::Header::rstTime() {
   gettimeofday(&time_,NULL);
}

//! Get syn flag
bool rpr::Header::getSyn() {
   return(getBit(0,7));
}

//! Get ack flag
bool rpr::Header::getAck() {
   return(getBit(0,6));
}

//! Set ack flag
void rpr::Header::setAck(bool state) {
   setBit(0,6,state);
}

//! Get eack flag
bool rpr::Header::getEAck() {
   return(getBit(0,5));
}

//! Set eack flag
void rpr::Header::setEAck(bool state) {
   setBit(0,5,state);
}

//! Get rst flag
bool rpr::Header::getRst() {
   return(getBit(0,4));
}

//! Set rst flag
void rpr::Header::setRst(bool state) {
   setBit(0,4,state);
}

//! Get NUL flag
bool rpr::Header::getNul() {
   return(getBit(0,3));
}

//! Set NUL flag
void rpr::Header::setNul(bool state) {
   setBit(0,3,state);
}

//! Get Busy flag
bool rpr::Header::getBusy() {
   return(getBit(0,0));
}

//! Set Busy flag
void rpr::Header::setBusy(bool state) {
   setBit(0,0,state);
}

//! Get sequence number
uint8_t rpr::Header::getSequence() {
   return(getUInt8(2));
}

//! Set sequence number
void rpr::Header::setSequence(uint8_t seq) {
   setUInt8(2,seq);
}

//! Get acknowledge number
uint8_t rpr::Header::getAcknowledge() {
   return(getUInt8(3));
}

//! Set acknowledge number
void rpr::Header::setAcknowledge(uint8_t ack) {
   setUInt8(3,ack);
}

//! Get version field
uint8_t rpr::Header::getVersion() {
   return(getUInt8(4) >> 4);
}

//! Set version field
void rpr::Header::setVersion(uint8_t version) {
   uint8_t val;

   val = getUInt8(4);

   val &= 0x0F;
   val |= version << 4;

   setUInt8(4,val);
}

//! Get chk flag
bool rpr::Header::getChk() {
   return(getBit(4,2));
}

//! Set chk flag
void rpr::Header::setChk(bool state) {
   setBit(4,2,state);
}

//! Get MAX Outstanding Segments
uint8_t rpr::Header::getMaxOutstandingSegments() {
   return(getUInt8(5));
}

//! Set MAX Outstanding Segments
void rpr::Header::setMaxOutstandingSegments(uint8_t max) {
   setUInt8(5,max);
}

//! Get MAX Segment Size
uint16_t rpr::Header::getMaxSegmentSize() {
   return(getUInt16(6));
}

//! Set MAX Segment Size
void rpr::Header::setMaxSegmentSize(uint16_t size) {
   setUInt16(6,size);
}

//! Get Retransmission Timeout
uint16_t rpr::Header::getRetransmissionTimeout() {
   return(getUInt16(8));
}

//! Set Retransmission Timeout
void rpr::Header::setRetransmissionTimeout(uint16_t to) {
   setUInt16(8,to);
}

//! Get Cumulative Acknowledgement Timeout
uint16_t rpr::Header::getCumulativeAckTimeout() {
   return(getUInt16(10));
}

//! Set Cumulative Acknowledgement Timeout
void rpr::Header::setCumulativeAckTimeout(uint16_t to) {
   setUInt16(10,to);
}

//! Get NULL Timeout
uint16_t rpr::Header::getNullTimeout() {
   return(getUInt16(12));
}

//! Set NULL Timeout
void rpr::Header::setNullTimeout(uint16_t to) {
   setUInt16(12,to);
}

//! Get Max Retransmissions
uint8_t rpr::Header::getMaxRetransmissions() {
   return(getUInt8(14));
}

//! Set Max Retransmissions
void rpr::Header::setMaxRetransmissions(uint8_t max) {
   setUInt8(14,max);
}

//! Get MAX Cumulative Ack
uint8_t rpr::Header::getMaxCumulativeAck() {
   return(getUInt8(15));
}

//! Set Max Cumulative Ack
void rpr::Header::setMaxCumulativeAck(uint8_t max) {
   setUInt8(15,max);
}

//! Get Timeout Unit
uint8_t rpr::Header::getTimeoutUnit() {
   return(getUInt8(17));
}

//! Set Timeout Unit
void rpr::Header::setTimeoutUnit(uint8_t unit) {
   setUInt8(17,unit);
}

//! Get Connection ID
uint32_t rpr::Header::getConnectionId() {
   return(getUInt32(18));
}

//! Set Timeout Unit
void rpr::Header::setConnectionId(uint32_t id) {
   setUInt32(18,id);
}

//! Dump message
std::string rpr::Header::dump() {
   uint32_t   x;

   std::stringstream ret("");

   ret << "   Total Size : " << std::dec << frame_->getBuffer(0)->getPayload() << std::endl;
   ret << "     Raw Size : " << std::dec << frame_->getBuffer(0)->getRawPayload() << std::endl;
   ret << "   Raw Header : ";

   for (x=0; x < getHeaderSize(); x++) {
      ret << "0x" << std::hex << std::setw(2) << std::setfill('0') << (uint32_t)getUInt8(x) << " ";
      if ( (x % 8) == 7 && (x+1) != getHeaderSize()) ret << std::endl << "                ";
   }
   ret << std::endl;

   ret << "       Verify : " << std::dec << verify() << std::endl;
   ret << "          Syn : " << std::dec << getSyn() << std::endl;
   ret << "          Ack : " << std::dec << getAck() << std::endl;
   ret << "         EAck : " << std::dec << getEAck() << std::endl;
   ret << "          Rst : " << std::dec << getRst() << std::endl;
   ret << "          Nul : " << std::dec << getNul() << std::endl;
   ret << "         Busy : " << std::dec << getBusy() << std::endl;
   ret << "     Sequence : " << std::dec << (uint32_t)getSequence() << std::endl;
   ret << "  Acknowledge : " << std::dec << (uint32_t)getAcknowledge() << std::endl;

   if ( ! getSyn() ) return(ret.str());

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

