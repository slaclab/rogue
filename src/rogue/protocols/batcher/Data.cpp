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
#include <thread>
#include <memory>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/protocols/batcher/Data.h>

namespace rpb = rogue::protocols::batcher;
namespace ris = rogue::interfaces::stream;

//! Class creation
rpb::DataPtr rpb::Data::create(ris::FrameIterator it, uint32_t size, uint8_t dest, uint8_t fUser, uint8_t lUser) {
   rpb::DataPtr p = std::make_shared<rpb::Data>(it, size, dest, fUser, lUser);
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

//! Return Begin Data Iterator
ris::FrameIterator rpb::Data::begin() {
   return it_;
}

//! Return End Data Iterator
ris::FrameIterator rpb::Data::end() {
   return it_ + size_;
}

//! Return Data Size
uint32_t rpb::Data::size() {
   return size_;
}

//! Return Data destination
uint8_t rpb::Data::dest() {
   return dest_;
}

//! Return First user
uint8_t rpb::Data::fUser() {
   return fUser_;
}

//! Return Last user
uint8_t rpb::Data::lUser() {
   return lUser_;
}

