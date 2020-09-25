/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Master Stream Interface
 * ----------------------------------------------------------------------------
 * File       : Variable.cpp
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Rogue stream master interface for EPICs variables
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

#include <rogue/protocols/epicsV3/Master.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <memory>

namespace ris = rogue::interfaces::stream;
namespace rpe = rogue::protocols::epicsV3;

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;

//! Setup class in python
void rpe::Master::setup_python() {

   bp::class_<rpe::Master, rpe::MasterPtr, bp::bases<rpe::Value, ris::Master>, boost::noncopyable >("Master",bp::init<std::string, uint32_t, std::string>());

   bp::implicitly_convertible<rpe::MasterPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpe::MasterPtr, rpe::ValuePtr>();
}

//! Class creation
rpe::Master::Master (std::string epicsName, uint32_t max, std::string type) : Value(epicsName) {

   // Init gdd record
   this->initGdd(type, false, 1, false);
   max_ = max;

   // Determine size in bytes & init data
   if ( epicsType_ == aitEnumUint8 ) {
      aitUint8 * pF = new aitUint8[1];
      pF[0] = 0;
      pValue_->putRef(pF, new rpe::Destructor<aitUint8 *>);
   }

   else if ( epicsType_ == aitEnumUint16 ) {
      aitUint16 * pF = new aitUint16[1];
      pF[0] = 0;
      pValue_->putRef(pF, new rpe::Destructor<aitUint16 *>);
   }

   else if ( epicsType_ == aitEnumUint32 ) {
      aitUint32 * pF = new aitUint32[1];
      pF[0] = 0;
      pValue_->putRef(pF, new rpe::Destructor<aitUint32 *>);
   }

   else if ( epicsType_ == aitEnumInt8 ) {
      aitInt8 * pF = new aitInt8[1];
      pF[0] = 0;
      pValue_->putRef(pF, new rpe::Destructor<aitInt8 *>);
   }

   else if ( epicsType_ == aitEnumInt16 ) {
      aitInt16 * pF = new aitInt16[1];
      pF[0] = 0;
      pValue_->putRef(pF, new rpe::Destructor<aitInt16 *>);
   }

   else if ( epicsType_ == aitEnumInt32 ) {
      aitInt32 * pF = new aitInt32[1];
      pF[0] = 0;
      pValue_->putRef(pF, new rpe::Destructor<aitInt32 *>);
   }

   else if ( epicsType_ == aitEnumFloat32 ) {
      aitFloat32 * pF = new aitFloat32[1];
      pF[0] = 0.0;
      pValue_->putRef(pF, new rpe::Destructor<aitFloat32 *>);
   }

   else if ( epicsType_ == aitEnumFloat64 ) {
      aitFloat64 * pF = new aitFloat64[1];
      pF[0] = 0.0;
      pValue_->putRef(pF, new rpe::Destructor<aitFloat64 *>);
   }
   else throw rogue::GeneralError("Master::Master","Invalid Type String: " + typeStr_);
}

rpe::Master::~Master() { }

bool rpe::Master::valueGet() { return true;}

bool rpe::Master::valueSet() {
   ris::FramePtr frame;
   ris::FrameIterator iter;
   uint32_t txSize;
   uint32_t i;

   txSize = size_ * fSize_;
   frame = reqFrame(txSize, true);
   frame->setPayload(txSize);

   iter = frame->begin();

   // Create vector of appropriate type
   if ( epicsType_ == aitEnumUint8 ) {
      aitUint8 * pF = new aitUint8[size_];
      pValue_->getRef(pF);
      for (i=0; i < size_; ++i) toFrame(iter,fSize_,&(pF[i]));
   }

   else if ( epicsType_ == aitEnumUint16 ) {
      aitUint16 * pF = new aitUint16[size_];
      pValue_->getRef(pF);
      for (i=0; i < size_; ++i) toFrame(iter,fSize_,&(pF[i]));
   }

   else if ( epicsType_ == aitEnumUint32 ) {
      aitUint32 * pF = new aitUint32[size_];
      pValue_->getRef(pF);
      for (i=0; i < size_; ++i) toFrame(iter,fSize_,&(pF[i]));
   }

   else if ( epicsType_ == aitEnumInt8 ) {
      aitInt8 * pF = new aitInt8[size_];
      pValue_->getRef(pF);
      for (i=0; i < size_; ++i) toFrame(iter,fSize_,&(pF[i]));
   }

   else if ( epicsType_ == aitEnumInt16 ) {
      aitInt16 * pF = new aitInt16[size_];
      pValue_->getRef(pF);
      for (i=0; i < size_; ++i) toFrame(iter,fSize_,&(pF[i]));
   }

   else if ( epicsType_ == aitEnumInt32 ) {
      aitInt32 * pF = new aitInt32[size_];
      pValue_->getRef(pF);
      for (i=0; i < size_; ++i) toFrame(iter,fSize_,&(pF[i]));
   }

   else if ( epicsType_ == aitEnumFloat32 ) {
      aitFloat32 * pF = new aitFloat32[size_];
      pValue_->getRef(pF);
      for (i=0; i < size_; ++i) toFrame(iter,fSize_,&(pF[i]));
   }

   else if ( epicsType_ == aitEnumFloat64 ) {
      aitFloat64 * pF = new aitFloat64[size_];
      pValue_->getRef(pF);
      for (i=0; i < size_; ++i) toFrame(iter,fSize_,&(pF[i]));
   }

   // Should this be pushed to a queue for a worker thread to call slaves?
   sendFrame(frame);
   return true;
}

