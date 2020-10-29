/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Stream Interface Rate Drop
 * ----------------------------------------------------------------------------
 * File          : RateDrop.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 08/25/2020
 *-----------------------------------------------------------------------------
 * Description :
 *    Drops frames at a specified rate.
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
#include <memory>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/RateDrop.h>
#include <rogue/Logging.h>
#include <sys/time.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::RateDropPtr ris::RateDrop::create(bool period, double value) {
   ris::RateDropPtr p = std::make_shared<ris::RateDrop>(period,value);
   return(p);
}

//! Setup class in python
void ris::RateDrop::setup_python() {
#ifndef NO_PYTHON
   bp::class_<ris::RateDrop, ris::RateDropPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("RateDrop",bp::init<bool,double>());
#endif
}

//! Creator with version constant
ris::RateDrop::RateDrop(bool period, double value) : ris::Master(), ris::Slave() {

   struct timeval currTime;
   uint32_t per;

   if ( (!period) || value == 0) {
      periodFlag_ = false;
      dropCount_  = (uint32_t)value;
      dropTarget_ = (uint32_t)value;
   }
   else {
      periodFlag_ = true;

      per = (uint32_t)(value * 1e6);

      div_t divResult = div(per,1000000);
      timePeriod_.tv_sec  = divResult.quot;
      timePeriod_.tv_usec = divResult.rem;

      gettimeofday(&currTime,NULL);
      timeradd(&currTime,&timePeriod_,&nextPeriod_);
   }
}

//! Deconstructor
ris::RateDrop::~RateDrop() {}

//! Accept a frame from master
void ris::RateDrop::acceptFrame ( ris::FramePtr frame ) {
   struct timeval currTime;

   // Dropping based upon frame count, if countPeriod_ is zero we never drop
   if ( ! periodFlag_ ) {
      if ( dropCount_++ == dropTarget_ ) {
         sendFrame(frame);
         dropCount_ = 0;
      }
   }

   // Dropping based upon time
   else {
      gettimeofday(&currTime,NULL);

      if (timercmp(&currTime,&(nextPeriod_),>) ) {
         sendFrame(frame);
         timeradd(&currTime,&timePeriod_,&nextPeriod_);
      }
   }
}

