/**
 *-----------------------------------------------------------------------------
 * Title      : Stream data source
 * ----------------------------------------------------------------------------
 * File       : StreamSrc.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2016-08-08
 * Last update: 2016-08-08
 * ----------------------------------------------------------------------------
 * Description:
 * Stream data source
 * ----------------------------------------------------------------------------
 * This file is part of the PGP card driver. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the PGP card driver, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
**/
#include "StreamSrc.h"
#include "StreamDest.h"
#include "PgpData.h"
#include <unistd.h>

#include <boost/python.hpp>

StreamSrc::StreamSrc() {
   runEn_    = false;
   running_  = false;
   name_     = "";
   lane_     = 0;
   vc_       = 0;
}

StreamSrc::~StreamSrc() {
}

void StreamSrc::setLaneVc(uint32_t lane, uint32_t vc) {
   lane_ = lane;
   vc_   = vc;
}

void StreamSrc::addDest( StreamDest *dest ) {
   destList_.push_back(dest);
}

PgpData * StreamSrc::destGetBuffer(uint32_t timeout) {
   if ( destList_.size() == 0 ) return(NULL);
   else {
      return(destList_[0]->getBuffer(timeout));
   }
}

bool StreamSrc::destPushBuffer ( PgpData * data ) {
   StreamDestList::iterator destIter;
   bool ret;

   if ( destList_.size() == 0 ) return(false);

   ret = true;
   data->lane = lane_;
   data->vc   = vc_;
   data->cont = 0;

   for (destIter = destList_.begin(); destIter != destList_.end(); destIter++) {
      if ( (*destIter)->doLock() ) {
         PyGILState_STATE pyState = PyGILState_Ensure();

         try {
            if ( (*destIter)->pushBuffer(data) == false ) ret = false;
         } catch (...) {
            PyErr_Print();
         }

         PyGILState_Release(pyState);
      } else {
         if ( (*destIter)->pushBuffer(data) == false ) ret = false;
      }
   }

   return(ret);
}

void StreamSrc::runThread() {
   running_ = false;
}

void * StreamSrc::staticThread ( void * p ) {
   StreamSrc *src = (StreamSrc *)p;

   src->runThread();
   pthread_exit(NULL);
   return(NULL);
}

bool StreamSrc::startThread() {
   runEn_   = true;
   if ( pthread_create(&thread_,NULL,staticThread,this) )
      return(false);
   else {
      pthread_setname_np(thread_,name_.c_str());
      return(true);
   }
}

void StreamSrc::stopThread() {
   runEn_ = false;
   pthread_join(thread_,NULL);
}

void StreamSrc::setName(std::string name) {
   name_ = name;
   if ( running_ ) pthread_setname_np(thread_,name_.c_str());
}

