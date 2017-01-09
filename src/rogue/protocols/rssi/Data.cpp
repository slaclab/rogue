/**
 *-----------------------------------------------------------------------------
 * Title      : RSII Data Class
 * ----------------------------------------------------------------------------
 * File       : Data.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Data
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
#include <rogue/protocols/rssi/Data.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>
#include <stdint.h>

namespace rpr = rogue::protocols::rssi;
namespace bp  = boost::python;

//! Class creation
rpr::DataPtr rpr::Data::create (uint8_t * data, uint32_t size) {
   rpr::DataPtr r = boost::make_shared<rpr::Data>(data,size);
   return(r);
}

// Setup python
void rpr::Data::setup_python () { }

//! Return required size
uint32_t rpr::Data::size(uint32_t dataSize) {
   return(dataSize + 8);
}

//! Creator
rpr::Data::Data ( uint8_t * data, uint32_t size) : rpr::Header(data,size) { }

//! Destructor
rpr::Data::~Data() { }

//! Return pointer to data
uint8_t * rpr::Data::getData() {
   return(data_ + 8);
}

//! Get data size
uint32_t rpr::Data::getDataSize() {
   return(size_ - 8);
}

