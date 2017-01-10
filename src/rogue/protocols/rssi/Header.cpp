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

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::HeaderPtr rpr::Header::create (ris::BufferPtr buff) {
   rpr::HeaderPtr r = boost::make_shared<rpr::Header>(buff);
   return(r);
}

//! Return required size
uint32_t rpr::Header::minSize() {
   return(HeaderSize);
}

//! Creator
rpr::Header::Header ( ris::BufferPtr buff) {
   if (buff_->getCount() < HeaderSize)
      throw(rogue::GeneralError::boundary("Header::Header", HeaderSize, buff_->getCount()));
   buff_ = buff;
   buff_->setHeadRoom(HeaderSize);
}

//! Destructor
rpr::Header::~Header() { }

//! Get header size
uint8_t rpr::Header::getHeaderSize() {
   return(buff_->getRawData()[0]);
}

//! Init header contents
void rpr::Header::init() {
   memset(buff_->getRawData(),0,HeaderSize);
   buff_->getRawData()[0] = HeaderSize;
}

//! Verify header contents
bool rpr::Header::verify() {
   uint16_t * val = (uint16_t *)&(buff_->getRawData()[6]);
   uint32_t   x;
   uint32_t   sum;

   sum = 0;
   for (x=0; x < (getHeaderSize()/2); x++) {
      sum += val[x];
   }

   return(true);
}

//! Update checksum
void rpr::Header::update() {
   uint16_t * val = (uint16_t *)&(buff_->getRawData()[6]);
   uint32_t   x;
   uint32_t   sum;

   sum = 0;
   for (x=0; x < ((getHeaderSize()/2)-2); x++) {
      sum += val[x];
   }

}

//! Get syn flag
bool rpr::Header::getSyn() {
   return(buff_->getRawData()[1]&0x80);
}

//! Set syn flag
void rpr::Header::setSyn(bool state) {
   buff_->getRawData()[1] &= 0x7F;
   if ( state ) buff_->getRawData()[1] |= 0x80;
}

//! Get ack flag
bool rpr::Header::getAck() {
   return(buff_->getRawData()[1]&0x40);
}

//! Set ack flag
void rpr::Header::setAck(bool state) {
   buff_->getRawData()[1] &= 0xBF;
   if ( state ) buff_->getRawData()[1] |= 0x40;
}

//! Get eack flag
bool rpr::Header::getEAck() {
   return(buff_->getRawData()[1]&0x20);
}

//! Set eack flag
void rpr::Header::setEAck(bool state) {
   buff_->getRawData()[1] &= 0xDF;
   if ( state ) buff_->getRawData()[1] |= 0x20;
}

//! Get rst flag
bool rpr::Header::getRst() {
   return(buff_->getRawData()[1]&0x10);
}

//! Set rst flag
void rpr::Header::setRst(bool state) {
   buff_->getRawData()[1] &= 0xEF;
   if ( state ) buff_->getRawData()[1] |= 0x10;
}

//! Get NUL flag
bool rpr::Header::getNul() {
   return(buff_->getRawData()[1]&0x08);
}

//! Set NUL flag
void rpr::Header::setNul(bool state) {
   buff_->getRawData()[1] &= 0xF7;
   if ( state ) buff_->getRawData()[1] |= 0x08;
}

//! Get Busy flag
bool rpr::Header::getBusy() {
   return(buff_->getRawData()[1]&0x01);
}

//! Set Busy flag
void rpr::Header::setBusy(bool state) {
   buff_->getRawData()[1] &= 0xFE;
   if ( state ) buff_->getRawData()[1] |= 0x01;
}

//! Get sequence number
uint16_t rpr::Header::getSequence() {
   return(buff_->getRawData()[3]);
}

//! Set sequence number
void rpr::Header::setSequence(uint16_t seq) {
   buff_->getRawData()[3] = seq;
}

//! Get acknowledge number
uint16_t rpr::Header::getAcknowledg() {
   return(buff_->getRawData()[2]);
}

//! Set acknowledge number
void rpr::Header::setAcknowledge(uint16_t ack) {
   buff_->getRawData()[2] = ack;
}

