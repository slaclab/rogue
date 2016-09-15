/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class, Stream destination
 * ----------------------------------------------------------------------------
 * File          : PrbsDataDest.cpp
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
#include "PrbsDataDest.h"
#include <unistd.h>
#include <stdlib.h>
#include "PgpData.h"

PrbsDataDest::PrbsDataDest() : PrbsData(), StreamDest(false) {
   this->errCount_ = 0;
   this->totCount_ = 0;
   this->totBytes_ = 0;
}

PrbsDataDest::~PrbsDataDest() { }

uint32_t PrbsDataDest::getErrors() {
   return(errCount_);
}

uint32_t PrbsDataDest::getCount() {
   return(totCount_);
}

uint32_t PrbsDataDest::getBytes() {
   return(totBytes_);
}

void PrbsDataDest::resetCount() {
   errCount_ = 0;
   totCount_ = 0;
   totBytes_ = 0;
}

bool PrbsDataDest::pushBuffer ( PgpData * buff ) {
   totCount_++;
   totBytes_ += buff->size;
 
   if ( ! processData ( buff->getData(), buff->size ) ) errCount_++;
   return(true);
}

