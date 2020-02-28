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
#include <memory>
#include <rogue/GilRelease.h>
#include <stdint.h>
#include <iomanip>
#include <rogue/interfaces/stream/Buffer.h>
#include <arpa/inet.h>
#include <iostream>
#include <sstream>
#include <string.h>
#include <sys/time.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;

//! Set 16-bit uint value
void rpr::Header::setUInt16 ( uint8_t *data, uint8_t byte, uint16_t value) {
   *((uint16_t *)(&(data[byte]))) = htons(value);
}

//! Get 16-bit uint value
uint16_t rpr::Header::getUInt16 ( uint8_t *data, uint8_t byte ) {
   return(ntohs(*((uint16_t *)(&(data[byte])))));
}

//! Set 32-bit uint value
void rpr::Header::setUInt32 ( uint8_t *data, uint8_t byte, uint32_t value) {
   *((uint32_t *)(&(data[byte]))) = htonl(value);
}

//! Get 32-bit uint value
uint32_t rpr::Header::getUInt32 ( uint8_t *data, uint8_t byte ) {
   return(ntohl(*((uint32_t *)(&(data[byte])))));
}

//! compute checksum
uint16_t rpr::Header::compSum (uint8_t *data, uint8_t size) {
   uint8_t  x;
   uint32_t sum;

   sum = 0;
   for (x=0; x < size-2; x = x+2) sum += getUInt16(data,x);

   sum = (sum % 0x10000) + (sum / 0x10000);
   sum = sum ^ 0xFFFF;
   return(sum);
}

//! Create
rpr::HeaderPtr rpr::Header::create(ris::FramePtr frame) {
   rpr::HeaderPtr r = std::make_shared<rpr::Header>(frame);
   return(r);
}

//! Creator
rpr::Header::Header(ris::FramePtr frame) {
   frame_ = frame;
   count_ = 0;

   syn = false;
   ack = false;
   rst = false;
   nul = false;
   busy = false;
   //sequence = 0;
   //acknowledge = 0;
   //version = 0;
   //chk = false;
   //maxOutstandingSegments = 0;
   //maxSegmentSize = 0;
   //retransmissionTimeout = 0;
   //cumulativeAckTimeout = 0;
   //nullTimeout = 0;
   //maxRetransmissions = 0;
   //maxCumulativeAck = 0;
   //timeoutUnit = 0;
   //connectionId = 0;
}

//! Destructor
rpr::Header::~Header() { }

//! Get Frame
ris::FramePtr rpr::Header::getFrame() {
   return(frame_);
}

//! Verify header contents
bool rpr::Header::verify() {
   uint8_t size;

   if ( frame_->isEmpty() ) return(false);

   ris::BufferPtr buff = *(frame_->beginBuffer());
   uint8_t * data = buff->begin();

   if ( buff->getPayload() < HeaderSize ) return(false);

   syn  = data[0] & 0x80;
   ack  = data[0] & 0x40;
   rst  = data[0] & 0x10;
   nul  = data[0] & 0x08;
   busy = data[0] & 0x01;

   size = (syn)?SynSize:HeaderSize;

   if ( (data[1] != size) || (buff->getPayload() < size) || (getUInt16(data,size-2) != compSum(data,size))) return false;

   sequence    = data[2];
   acknowledge = data[3];

   if ( ! syn ) return true;

   version = data[4] >> 4;
   chk  = data[4] & 0x04;

   maxOutstandingSegments = data[5];
   maxSegmentSize = getUInt16(data,6);
   retransmissionTimeout = getUInt16(data,8);
   cumulativeAckTimeout = getUInt16(data,10);
   nullTimeout = getUInt16(data,12);
   maxRetransmissions = data[14];
   maxCumulativeAck = data[15];
   timeoutUnit = data[17];
   connectionId = data[18];

   return(true);
}

//! Update checksum, set tx time and increment tx count
void rpr::Header::update() {
   uint8_t size;

   if ( frame_->isEmpty() )
      throw(rogue::GeneralError("Header::update","Frame is empty!"));

   ris::BufferPtr buff = *(frame_->beginBuffer());
   uint8_t * data = buff->begin();

   size = (syn)?SynSize:HeaderSize;

   if ( buff->getSize() < size )
      throw(rogue::GeneralError::create("rssi::Header::update",
               "Buffer size %i is less size indicated in header %i",
               buff->getSize(), size));

   buff->minPayload(size);

   memset(data,0,size);
   data[1] = size;

   if ( ack  ) data[0] |= 0x40;
   if ( rst  ) data[0] |= 0x10;
   if ( nul  ) data[0] |= 0x08;
   if ( busy ) data[0] |= 0x01;

   data[2] = sequence;
   data[3] = acknowledge;

   if ( syn ) {
      data[0] |= 0x80;
      data[4] |= 0x08;
      data[4] |= (version << 4);
      if ( chk ) data[4] |= 0x04;

      data[5] = maxOutstandingSegments;

      setUInt16(data,6,maxSegmentSize);
      setUInt16(data,8,retransmissionTimeout);
      setUInt16(data,10,cumulativeAckTimeout);
      setUInt16(data,12,nullTimeout);

      data[14] = maxRetransmissions;
      data[15] = maxCumulativeAck;
      data[17] = timeoutUnit;
      data[18] = connectionId;
   }

   setUInt16(data,size-2,compSum(data,size));
   gettimeofday(&time_,NULL);
   count_++;
}

//! Get time
struct timeval & rpr::Header::getTime() {
   return(time_);
}

//! Get Count
uint32_t rpr::Header::count() {
   return(count_);
}

//! Reset timer
void rpr::Header::rstTime() {
   gettimeofday(&time_,NULL);
}

//! Dump message
std::string rpr::Header::dump() {
   uint32_t   x;

   ris::BufferPtr buff = *(frame_->beginBuffer());
   uint8_t * data = buff->begin();

   std::stringstream ret("");

   ret << "   Total Size : " << std::dec << (*(frame_->beginBuffer()))->getPayload() << std::endl;
   ret << "     Raw Size : " << std::dec << (*(frame_->beginBuffer()))->getSize() << std::endl;
   ret << "   Raw Header : ";

   for (x=0; x < data[1]; x++) {
      ret << "0x" << std::hex << std::setw(2) << std::setfill('0') << (uint32_t)data[x] << " ";
      if ( (x % 8) == 7 && (x+1) != data[1]) ret << std::endl << "                ";
   }
   ret << std::endl;

   ret << "          Syn : " << std::dec << syn << std::endl;
   ret << "          Ack : " << std::dec << ack << std::endl;
   ret << "          Rst : " << std::dec << rst << std::endl;
   ret << "          Nul : " << std::dec << nul << std::endl;
   ret << "         Busy : " << std::dec << busy << std::endl;
   ret << "     Sequence : " << std::dec << (uint32_t)sequence << std::endl;
   ret << "  Acknowledge : " << std::dec << (uint32_t)acknowledge << std::endl;

   if ( ! syn ) return(ret.str());

   ret << "      Version : " << std::dec << (uint32_t)version << std::endl;
   ret << "          Chk : " << std::dec << chk << std::endl;
   ret << "  Max Out Seg : " << std::dec << (uint32_t)maxOutstandingSegments << std::endl;
   ret << " Max Seg Size : " << std::dec << (uint32_t)maxSegmentSize << std::endl;
   ret << "  Retran Tout : " << std::dec << (uint32_t)retransmissionTimeout << std::endl;
   ret << " Cum Ack Tout : " << std::dec << (uint32_t)cumulativeAckTimeout << std::endl;
   ret << "    Null Tout : " << std::dec << (uint32_t)nullTimeout << std::endl;
   ret << "  Max Retrans : " << std::dec << (uint32_t)maxRetransmissions << std::endl;
   ret << "  Max Cum Ack : " << std::dec << (uint32_t)maxCumulativeAck << std::endl;
   ret << " Timeout Unit : " << std::dec << (uint32_t)timeoutUnit << std::endl;
   ret << "      Conn Id : " << std::dec << (uint32_t)connectionId << std::endl;

   return(ret.str());
}

