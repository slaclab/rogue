/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class, Stream source
 * ----------------------------------------------------------------------------
 * File          : PrbsDataSrc.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 08/11/2014
 * Last update   : 08/11/2014
 *-----------------------------------------------------------------------------
 * Description :
 *    Class used to generate and receive PRBS test data.
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
#include "PrbsDataSrc.h"
#include <unistd.h>
#include <stdlib.h>
#include <PgpData.h>

PrbsDataSrc::PrbsDataSrc(uint32_t size) : PrbsData(), StreamSrc() {
   this->size_     = size;
   this->totCount_ = 0;
   this->totBytes_ = 0;
}

PrbsDataSrc::~PrbsDataSrc() {
   stopThread();
}

void PrbsDataSrc::runThread() {
   PgpData * buff;

   running_ = true;

   while(runEn_) {
   //while(totCount_ < 5) {

      if ( (buff=destGetBuffer(100)) != NULL ) {
         if ( size_ <= buff->getMaxSize() ) buff->size = size_;
         else buff->size = buff->getMaxSize();

         genData(buff->getData(),buff->size);
         destPushBuffer ( buff);
         totCount_++;
         totBytes_ += buff->size;
      }
   }
   running_ = false;
}

uint32_t PrbsDataSrc::getCount() {
   return(totCount_);
}

uint32_t PrbsDataSrc::getBytes() {
   return(totBytes_);
}

void PrbsDataSrc::resetCount() {
   totCount_ = 0;
   totBytes_ = 0;
}

void PrbsDataSrc::enable() {
   startThread();
}

void PrbsDataSrc::disable() {
   stopThread();
}

