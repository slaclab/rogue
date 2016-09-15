/**
 *-----------------------------------------------------------------------------
 * Title      : Stream data destination
 * ----------------------------------------------------------------------------
 * File       : StreamDest.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream data destination
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
#include "StreamDest.h"
#include "PgpData.h"

StreamDest::StreamDest() {
   this->doLock_=true;
}

StreamDest::StreamDest(bool lock) {
   this->doLock_ = lock;
}

StreamDest::StreamDest(const StreamDest &dest) {
   doLock_ = dest.doLock_;
}

StreamDest::~StreamDest() { 
}

PgpData * StreamDest::getBuffer(uint32_t timeout) {
   usleep(timeout);
   return(NULL);
}

bool StreamDest::pushBuffer ( PgpData *data) {
   return(false);
}

bool StreamDest::doLock() {
   return(doLock_);
}

bool StreamDestWrap::pushBuffer ( PgpData *data ) {
   if (boost::python::override pb = this->get_override("pushBuffer")) 
      return(pb(boost::ref(data)));
   else 
      return(StreamDest::pushBuffer(data));
}

bool StreamDestWrap::defPushBuffer( PgpData *data) {
   return(StreamDest::pushBuffer(data));
}

