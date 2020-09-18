/**
 *-----------------------------------------------------------------------------
 * Title      : Rogue EPICS V3 Interface: Stream Slave Interface
 * ----------------------------------------------------------------------------
 * File       : Slave.cpp
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Stream slave to epics variables
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

#include <rogue/protocols/epicsV3/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/GeneralError.h>
#include <rogue/GilRelease.h>
#include <memory>
#include <memory>

#ifdef __MACH__
#include <mach/clock.h>
#include <mach/mach.h>
#endif

namespace ris = rogue::interfaces::stream;
namespace rpe = rogue::protocols::epicsV3;

#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;

//! Setup class in python
void rpe::Slave::setup_python() {

   bp::class_<rpe::Slave, rpe::SlavePtr, bp::bases<rpe::Value, ris::Slave>, boost::noncopyable >("Slave",bp::init<std::string, uint32_t, std::string>());

   bp::implicitly_convertible<rpe::SlavePtr, ris::SlavePtr>();
   bp::implicitly_convertible<rpe::SlavePtr, rpe::ValuePtr>();
}

//! Class creation
rpe::Slave::Slave (std::string epicsName, uint32_t max, std::string type) : Value(epicsName) {

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
   else throw rogue::GeneralError("Slave::Slave","Invalid Type String: " + typeStr_);
}

rpe::Slave::~Slave() { }

bool rpe::Slave::valueGet() { return true; }

bool rpe::Slave::valueSet() { return true; }

void rpe::Slave::acceptFrame ( ris::FramePtr frame ) {
   ris::FrameIterator iter;
   struct timespec t;
   uint32_t fSize;
   uint32_t size_;
   uint32_t i;

   rogue::GilRelease noGil;
   ris::FrameLockPtr fLock = frame->lock();

   if ( frame->getError() ) {
      rpe::Value::log_->error("Got errored frame = 0x%i",frame->getError());
      return; // Invalid frame, drop it
   }

   fSize = frame->getPayload();
   iter = frame->begin();

   // First check to see if frame is valid
   if ( (fSize % fSize_) != 0 ) {
      rpe::Value::log_->error("Invalid frame size (%i) from epics: %s\n",fSize,epicsName_.c_str());
      return;
   }

   // Compute element count
   size_ = fSize / fSize_;

   // Limit size
   if ( size_ > max_ ) size_ = max_;

   {
      std::lock_guard<std::mutex> lock(rpe::Value::mtx_);

      // Release old data
      pValue_->unreference();
      pValue_ = new gddAtomic (gddAppType_value, epicsType_, 1u, size_);

      // Set timestamp
#ifdef __MACH__ // OSX does not have clock_gettime
      clock_serv_t cclock;
      mach_timespec_t mts;
      host_get_clock_service(mach_host_self(), CALENDAR_CLOCK, &cclock);
      clock_get_time(cclock, &mts);
      mach_port_deallocate(mach_task_self(), cclock);
      t.tv_sec = mts.tv_sec;
      t.tv_nsec = mts.tv_nsec;
#else
      clock_gettime(CLOCK_REALTIME,&t);
#endif
      pValue_->setTimeStamp(&t);

      // Create vector of appropriate type
      if ( epicsType_ == aitEnumUint8 ) {
         aitUint8 * pF = new aitUint8[size_];
         for (i=0; i < size_; ++i) fromFrame(iter,fSize_,&(pF[i]));
         pValue_->putRef(pF, new rpe::Destructor<aitUint8 *>);
      }

      else if ( epicsType_ == aitEnumUint16 ) {
         aitUint16 * pF = new aitUint16[size_];
         for (i=0; i < size_; ++i) fromFrame(iter,fSize_,&(pF[i]));
         pValue_->putRef(pF, new rpe::Destructor<aitUint16 *>);
      }

      else if ( epicsType_ == aitEnumUint32 ) {
         aitUint32 * pF = new aitUint32[size_];
         for (i=0; i < size_; ++i) fromFrame(iter,fSize_,&(pF[i]));
         pValue_->putRef(pF, new rpe::Destructor<aitUint32 *>);
      }

      else if ( epicsType_ == aitEnumInt8 ) {
         aitInt8 * pF = new aitInt8[size_];
         for (i=0; i < size_; ++i) fromFrame(iter,fSize_,&(pF[i]));
         pValue_->putRef(pF, new rpe::Destructor<aitInt8 *>);
      }

      else if ( epicsType_ == aitEnumInt16 ) {
         aitInt16 * pF = new aitInt16[size_];
         for (i=0; i < size_; ++i) fromFrame(iter,fSize_,&(pF[i]));
         pValue_->putRef(pF, new rpe::Destructor<aitInt16 *>);
      }

      else if ( epicsType_ == aitEnumInt32 ) {
         aitInt32 * pF = new aitInt32[size_];
         for (i=0; i < size_; ++i) fromFrame(iter,fSize_,&(pF[i]));
         pValue_->putRef(pF, new rpe::Destructor<aitInt32 *>);
      }

      else if ( epicsType_ == aitEnumFloat32 ) {
         aitFloat32 * pF = new aitFloat32[size_];
         for (i=0; i < size_; ++i) fromFrame(iter,fSize_,&(pF[i]));
         pValue_->putRef(pF, new rpe::Destructor<aitFloat32 *>);
      }

      else if ( epicsType_ == aitEnumFloat64 ) {
         aitFloat64 * pF = new aitFloat64[size_];
         for (i=0; i < size_; ++i) fromFrame(iter,fSize_,&(pF[i]));
         pValue_->putRef(pF, new rpe::Destructor<aitFloat64 *>);
      }
   }

   updated();
}

