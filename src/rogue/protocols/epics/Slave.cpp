/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs PV Attribute Object
 * ----------------------------------------------------------------------------
 * File       : Slave.cpp
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Slave to epics gateway.
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

#include <boost/python.hpp>
#include <rogue/protocols/epics/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/GeneralError.h>
#include <rogue/ScopedGil.h>
#include <rogue/GilRelease.h>
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>

namespace ris = rogue::interfaces::stream;
namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Slave::setup_python() {

   bp::class_<rpe::Slave, rpe::SlavePtr, boost::noncopyable >("Slave",bp::init<std::string, uint32_t, std::string>());

   bp::implicitly_convertible<rpe::SlavePtr, ris::SlavePtr>();
   bp::implicitly_convertible<rpe::SlavePtr, rpe::ValuePtr>();
}

//! Class creation
rpe::Slave::Slave (std::string epicsName, uint32_t max, std::string type) : Value(epicsName) {
   max_ = max;

   // Init gdd record
   this->initGdd(type, false, max_);

   // Determine size in bytes
   if      ( epicsType_ == aitEnumUint8  || epicsType_ == aitEnumInt8  ) fSize_ = 1;
   else if ( epicsType_ == aitEnumUint16 || epicsType_ == aitEnumInt16 ) fSize_ = 2;
   else if ( epicsType_ == aitEnumUint32 || epicsType_ == aitEnumInt32 ||
             epicsType_ == aitEnumFloat32 ) fSize_ = 4;
   else if ( epicsType_ == aitEnumFloat64 ) fSize_ = 8;
   else throw rogue::GeneralError("Slave::Slave","Invalid Type String: " + typeStr_);
}

rpe::Slave::~Slave() { }

void rpe::Slave::valueGet() { }

void rpe::Slave::valueSet() { }

void rpe::Slave::acceptFrame ( ris::FramePtr frame ) {
   struct timespec t;
   uint32_t tSize;
   uint32_t bSize;
   uint32_t pos;
   void   * pF;

   tSize = frame->getPayload();

   // Limit size
   if ( tSize > max_ ) tSize = max_;

   // First check to see if frame is valid
   if ( (tSize % fSize_) != 0 ) {
      rpe::Value::log_->error("Invalid frame size (%i) from epics: %s\n",tSize,epicsName_.c_str());
      return;
   }
   bSize = tSize / fSize_;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(rpe::Value::mtx_);

   // Release old data
   pValue_->unreference();
   pValue_ = new gddAtomic (gddAppType_value, epicsType_, 1u, bSize);
   pF = NULL;

   // Set timestamp
   clock_gettime(CLOCK_REALTIME,&t);
   pValue_->setTimeStamp(&t);

   // Create vector of appropriate type
   if ( epicsType_ == aitEnumUint8 ) {
      pF = new aitUint8[bSize];
      pValue_->putRef((aitUint8 *)pF, new rpe::Destructor<aitUint8 *>);
   }

   else if ( epicsType_ == aitEnumUint16 ) {
      pF = new aitUint16[bSize];
      pValue_->putRef((aitUint16 *)pF, new rpe::Destructor<aitUint16 *>);
   }

   else if ( epicsType_ == aitEnumUint32 ) {
      pF = new aitUint32[bSize];
      pValue_->putRef((aitUint32 *)pF, new rpe::Destructor<aitUint32 *>);
   }

   else if ( epicsType_ == aitEnumInt8 ) {
      pF = new aitInt8[bSize];
      pValue_->putRef((aitInt8 *)pF, new rpe::Destructor<aitInt8 *>);
   }

   else if ( epicsType_ == aitEnumInt16 ) {
      pF = new aitInt16[bSize];
      pValue_->putRef((aitInt16 *)pF, new rpe::Destructor<aitInt16 *>);
   }

   else if ( epicsType_ == aitEnumInt32 ) {
      pF = new aitInt32[bSize];
      pValue_->putRef((aitInt32 *)pF, new rpe::Destructor<aitInt32 *>);
   }

   else if ( epicsType_ == aitEnumFloat32 ) {
      pF = new aitFloat32[bSize];
      pValue_->putRef((aitFloat32 *)pF, new rpe::Destructor<aitFloat32 *>);
   }

   else if ( epicsType_ == aitEnumFloat64 ) {
      pF = new aitFloat64[bSize];
      pValue_->putRef((aitFloat64 *)pF, new rpe::Destructor<aitFloat64 *>);
   }

   // Copy the data
   if ( pF != NULL ) {
      pos = 0;
      while (pos < tSize) pos += frame->read(pF, pos, fSize_);
      updated();
   }
}

