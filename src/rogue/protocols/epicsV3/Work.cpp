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

#include <boost/python.hpp>
namespace bp  = boost::python;

//! Create a work container
rpe::WorkPtr create ( rpe::ValuePtr value, gdd & gValue, casAsyncReadIO *read, casAsyncWriteIO *write) {
   rpe::WorkPtr m = boost::make_shared<rpe::Work>(value,gValue,read,write);
   return(m);
}

rpe::Work::Work ( rpe::ValuePtr value, gdd & gValue, casAsyncReadIO *read, casAsyncWriteIO *write ) 
   : value_(value), gValue_(gValue), read_(read), write_(write)
{
}

void rpe::Work::execute () {
   caStatus ret;

   if ( this->read_ != NULL ) {
      ret = this->value_->read(this->gValue_);
      this->read_->postIOCompletion(ret, this->gValue_);
   }
   
   else if ( this->write_ != NULL ) {
      ret = this->value_->write(this->gValue_);
      this->write_->postIOCompletion(ret);
   }
}

