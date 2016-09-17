/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface master
 * ----------------------------------------------------------------------------
 * File       : Master.h
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-09-16
 * Last update: 2016-09-16
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
#include <boost/make_shared.hpp>

namespace is = interfaces::stream;

//! Class creation
is::MasterPtr is::Master::create () {
   is::MasterPtr msg = boost::make_shared<is::Master>();
   return(msg);
}

//! Creator
is::Master::Master() {}

//! Destructor
is::Master::~Master() {
   primary_ = is::Slave::create();
   slaves_.clear();
}

//! Set primary slave, used for buffer request forwarding
void is::Master::setSlave ( boost::shared_ptr<interfaces::stream::Slave> slave ) {
   slaves_.push_back(slave);
   primary_ = slave;
}

//! Add secondary slave
void is::Master::addSlave ( is::SlavePtr slave ) {
   slaves_.push_back(slave);
}

//! Request frame from primary slave
is::FramePtr is::Master::reqFrame ( uint32_t size, bool zeroCopyEn) {
   return(primary_->acceptReq(size,zeroCopyEn));
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

