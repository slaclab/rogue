/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Batcher Data
 * ----------------------------------------------------------------------------
 * File          : Data.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 02/08/2019
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#include <stdint.h>
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>
#include <rogue/interfaces/stream/FrameIterator.h>

namespace rpb = rogue::protocols:batcher;
namespace ris = rogue::interfaces::stream;

//! Class creation
rpb::DataPtr rp::Data::create(ris::FrameIterator it, uint32_t size, uint8_t dest, uint8_t fUser, uint8_t lUser) {
   rpb::DataPtr p = boost::make_shared<rpb::Data>(it, size, dest, fUser, lUser);
   return(p);
}

//! Setup class in python
void rpb::Data::setup_python() { }

//! Creator with version constant
rpb::Data::Data(ris::FrameIterator it, uint32_t size, uint8_t dest, uint8_t fUser, uint8_t lUser) {
   it_    = it; // Copy
   size_  = size;   
   dest_  = dest;   
   fUser_ = fUser;
   lUser_ = lUser;
}

//! Deconstructor
rpb::Data::~Data() {}

//! Return Data Iterator
ris::FrameIterator & rpb::Data::iterator() {
   return it_;
}

//! Return Data Size
uint32_t rpb::data::size() {
   return size_;
}

//! Return Data destination
uint8_t rpb::data::dest() {
   return dest_;
}

//! Return First user
uint8_t rpb::data::fUser() {
   return fUser_;
}

//! Return Last user
uint8_t rpb::data::lUser() {
   return lUser_;
}

