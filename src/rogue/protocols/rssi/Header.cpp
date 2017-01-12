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

   frame_->getBuffer(0)->getRawData()[byte] &= (0xFF ^ (1 << bit));

   if ( value ) frame_->getBuffer(0)->getRawData()[byte] |= (1 << bit);
}

//! Get bit value
bool rpr::Header::getBit ( uint8_t byte, uint8_t bit) {
   if ( bit > 7 )
      throw(rogue::GeneralError::boundary("Header::getBit",bit,7));

   if ( byte >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::getBit",byte,getHeaderSize()-1));

   return(((frame_->getBuffer(0)->getRawData()[byte] >> bit) & 0x1) != 0);
}

//! Set 8-bit uint value
void rpr::Header::setUInt8 ( uint8_t byte, uint8_t value) {
   if ( byte >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::setUInt8",byte,getHeaderSize()));

   frame_->getBuffer(0)->getRawData()[byte] = value;
}

//! Get 8-bit uint value
uint8_t rpr::Header::getUInt8 ( uint8_t byte ) {
   if ( byte >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::getUInt8",byte,getHeaderSize()));

   return(frame_->getBuffer(0)->getRawData()[byte]);
}

//! Set 16-bit uint value
void rpr::Header::setUInt16 ( uint8_t byte, uint16_t value) {
   if ( (byte+1) >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::setUInt16",byte+1,getHeaderSize()));

   *((uint16_t *)(&(frame_->getBuffer(0)->getRawData()[byte]))) = htons(value);
}

//! Get 16-bit uint value
uint16_t rpr::Header::getUInt16 ( uint8_t byte ) {
   if ( (byte+1) >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::getUInt16",byte+1,getHeaderSize()));

   return(ntohs(*((uint16_t *)(&(frame_->getBuffer(0)->getRawData()[byte])))));
}

//! Set 32-bit uint value
void rpr::Header::setUInt32 ( uint8_t byte, uint32_t value) {
   if ( (byte+3) >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::setUInt32",byte+3,getHeaderSize()));

   *((uint32_t *)(&(frame_->getBuffer(0)->getRawData()[byte]))) = htonl(value);
}

//! Get 32-bit uint value
uint32_t rpr::Header::getUInt32 ( uint8_t byte ) {
   if ( (byte+3) >= getHeaderSize() )
      throw(rogue::GeneralError::boundary("Header::getUInt32",byte+3,getHeaderSize()));

   return(ntohl(*((uint32_t *)(&(frame_->getBuffer(0)->getRawData()[byte])))));
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
   frame_ = frame;
}

//! Destructor
rpr::Header::~Header() { }

//! Get Frame
ris::FramePtr rpr::Header::getFrame() {
   return(frame_);
}

//! Return required size
uint32_t rpr::Header::minSize() {
   return(HeaderSize);
}

//! Get header size
uint8_t rpr::Header::getHeaderSize() {
   return(frame_->getBuffer(0)->getRawData()[1]);
}

//! Init header contents
void rpr::Header::init(bool setSize) {

   if ( frame_->getCount() != 1 ) 
      throw(rogue::GeneralError("Header::init","Frame must contain a single buffer"));

   if ( frame_->getBuffer(0)->getRawSize() < minSize() ) 
      throw(rogue::GeneralError::boundary("Header::init",minSize(),frame_->getBuffer(0)->getRawSize()));

   memset(frame_->getBuffer(0)->getRawData(),0,minSize());
   frame_->getBuffer(0)->getRawData()[1] = minSize();
   if ( setSize ) frame_->getBuffer(0)->setSize(minSize());
}

//! Verify header contents
bool rpr::Header::verify() {
   return(getUInt16(getHeaderSize()-2) == compSum());
}

//! Update checksum
void rpr::Header::update() {
   setUInt16(getHeaderSize()-2,compSum());
}

//! Get syn flag
bool rpr::Header::getSyn() {
   return(getBit(0,7));
}

//! Set syn flag
void rpr::Header::setSyn(bool state) {
   setBit(0,7,state);
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
uint16_t rpr::Header::getSequence() {
   return(getUInt16(2));
}

//! Set sequence number
void rpr::Header::setSequence(uint16_t seq) {
   setUInt16(2,seq);
}

//! Get acknowledge number
uint16_t rpr::Header::getAcknowledge() {
   return(getUInt16(3));
}

//! Set acknowledge number
void rpr::Header::setAcknowledge(uint16_t ack) {
   setUInt16(3,ack);
}

//! Dump message
std::string rpr::Header::dump() {
   uint32_t   x;

   std::stringstream ret("");

   ret << "   Total Size : " << std::dec << frame_->getBuffer(0)->getCount() << std::endl;
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
   ret << "     Sequence : " << std::dec << getSequence() << std::endl;
   ret << "  Acknowledge : " << std::dec << getAcknowledge() << std::endl;

   return(ret.str());
}

