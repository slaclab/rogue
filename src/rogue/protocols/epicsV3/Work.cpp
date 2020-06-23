/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Work Unit
 * ----------------------------------------------------------------------------
 * File       : Work.cpp
 * Created    : 2019-01-19
 * ----------------------------------------------------------------------------
 * Description:
 * Class to store an EPICs work unit (read or write)
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

#include <rogue/protocols/epicsV3/Work.h>
#include <rogue/protocols/epicsV3/Value.h>
#include <time.h>

namespace rpe = rogue::protocols::epicsV3;

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;

//! Create a work container for write
rpe::WorkPtr rpe::Work::createWrite ( rpe::ValuePtr value, const gdd & wValue, casAsyncWriteIO *write) {
   rpe::WorkPtr m = std::make_shared<rpe::Work>(value,wValue,write);
   return(m);
}

//! Create a work container for read
rpe::WorkPtr rpe::Work::createRead ( rpe::ValuePtr value, gdd & rValue, casAsyncReadIO *read) {
   rpe::WorkPtr m = std::make_shared<rpe::Work>(value,rValue,read);
   return(m);
}

rpe::Work::Work ( rpe::ValuePtr value, const gdd & wValue, casAsyncWriteIO *write) {
   value_  = value;
   write_  = write;
   read_   = NULL;
   gValue_ = (gdd *)(&wValue);
   gValue_->reference();
}

rpe::Work::Work ( rpe::ValuePtr value, gdd & rValue, casAsyncReadIO *read) {
   value_  = value;
   write_  = NULL;
   read_   = read;
   gValue_ = (gdd *)(&rValue);
   gValue_->reference();
}

rpe::Work::~Work() {
   gValue_->unreference();
}

void rpe::Work::execute () {
   caStatus ret;

   if ( this->read_ != NULL ) {
      ret = this->value_->read(*(this->gValue_));
      this->read_->postIOCompletion(ret, *(this->gValue_));
   }

   else if ( this->write_ != NULL ) {
      ret = this->value_->write(*(this->gValue_));
      this->write_->postIOCompletion(ret);
   }
}

