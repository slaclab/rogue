/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface master
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
#include <unistd.h>
#include <interfaces/stream/Slave.h>
#include <interfaces/stream/Master.h>
#include <interfaces/stream/Frame.h>

#include <boost/python.hpp>

namespace is = interfaces::stream;

//! Creator
is::Master::Master() {}

//! Destructor
is::Master::~Master() {
   slaves_.clear();
}

//! Set frame slave
void is::Master::addSlave ( is::SlavePtr slave ) {
   slaves_.push_back(slave);
}

//! Request frame from slave
/*
 * An allocate command will be issued to each slave until one returns a buffer. 
 * If none return a buffer a null pointer will be returned.
 */
is::FramePtr is::Master::reqFrame ( uint32_t size, bool zeroCopyEn) {
   uint32_t x;

   is::FramePtr f;

   for (x=0; x < slaves_.size(); x++)
      if ( f = slaves_[x]->acceptReq(size,zeroCopyEn) ) break;

   return(f);
}

//! Push frame to slaves
bool is::Master::sendFrame ( FramePtr frame ) {
   uint32_t x;
   bool     ret;

   if ( slaves_.size() == 0 ) return(false);

   ret = true;

   for (x=0; x < slaves_.size(); x++) {
      if ( slaves_[x]->acceptFrame(frame) == false ) ret = false;
   }

   return(ret);
}

