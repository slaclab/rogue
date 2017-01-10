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
#include <boost/make_shared.hpp>
#include <rogue/common.h>
#include <stdint.h>

namespace rpr = rogue::protocols::rssi;
namespace bp  = boost::python;

//! Class creation
rpr::HeaderPtr rpr::Header::create (uint8_t * data, uint32_t size) {
   rpr::HeaderPtr r = boost::make_shared<rpr::Header>(data,size);
   return(r);
}

//! Return required size
uint32_t rpr::Header::size() {
   return(8);
}

//! Creator
rpr::Header::Header ( uint8_t * data, uint32_t size) {
   data_ = data;
   size_ = size;
}

//! Destructor
rpr::Header::~Header() { }

//! Get header size
uint8_t rpr::Header::getHeaderSize() {
   return(data_[0]);
}

//! Init header contents
void rpr::Header::init() {
   memset(data_,0,8);
   data_[0] = 8;
}

//! Verify header contents
bool rpr::Header::verify() {
   return(true);

}

//! Update checksum
void rpr::Header::update() {

}

//! Get syn flag
bool rpr::Header::getSyn() {
   return(data_[1]&0x80);
}

//! Set syn flag
void rpr::Header::setSyn(bool state) {
   data_[1] &= 0x7F;
   if ( state ) data_[1] |= 0x80;
}

//! Get ack flag
bool rpr::Header::getAck() {
   return(data_[1]&0x40);
}

//! Set ack flag
void rpr::Header::setAck(bool state) {
   data_[1] &= 0xBF;
   if ( state ) data_[1] |= 0x40;
}

//! Get eack flag
bool rpr::Header::getEAck() {
   return(data_[1]&0x20);
}

//! Set eack flag
void rpr::Header::setEAck(bool state) {
   data_[1] &= 0xDF;
   if ( state ) data_[1] |= 0x20;
}

//! Get rst flag
bool rpr::Header::getRst() {
   return(data_[1]&0x10);
}

//! Set rst flag
void rpr::Header::setRst(bool state) {
   data_[1] &= 0xEF;
   if ( state ) data_[1] |= 0x10;
}

//! Get NUL flag
bool rpr::Header::getNul() {
   return(data_[1]&0x08);
}

//! Set NUL flag
void rpr::Header::setNul(bool state) {
   data_[1] &= 0xF7;
   if ( state ) data_[1] |= 0x08;
}

//! Get Busy flag
bool rpr::Header::getBusy() {
   return(data_[1]&0x01);
}

//! Set Busy flag
void rpr::Header::setBusy(bool state) {
   data_[1] &= 0xFE;
   if ( state ) data_[1] |= 0x01;
}

//! Get sequence number
uint16_t rpr::Header::getSequence() {
   return(data_[3]);
}

//! Set sequence number
void rpr::Header::setSequence(uint16_t seq) {
   data_[3] = seq;
}

//! Get acknowledge number
uint16_t rpr::Header::getAcknowledg() {
   return(data_[2]);
}

//! Set acknowledge number
void rpr::Header::setAcknowledge(uint16_t ack) {
   data_[2] = ack;
}


