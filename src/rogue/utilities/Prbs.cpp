/**
 *-----------------------------------------------------------------------------
 * Title         : PRBS Receive And Transmit Class
 * ----------------------------------------------------------------------------
 * File          : Prbs.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
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
#include <unistd.h>
#include <stdarg.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/utilities/Prbs.h>
#include <boost/make_shared.hpp>
#include <rogue/GilRelease.h>
#include <rogue/GeneralError.h>
#include <rogue/Logging.h>
#include <rogue/GeneralError.h>

namespace ris = rogue::interfaces::stream;
namespace ru  = rogue::utilities;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ru::PrbsPtr ru::Prbs::create () {
   ru::PrbsPtr p = boost::make_shared<ru::Prbs>();
   return(p);
}

//! Creator with default taps and size
ru::Prbs::Prbs() {
   txThread_   = NULL;
   rxSeq_      = 0;
   rxErrCount_ = 0;
   rxCount_    = 0;
   rxBytes_    = 0;
   txSeq_      = 0;
   txSize_     = 0;
   txErrCount_ = 0;
   txCount_    = 0;
   txBytes_    = 0;
   checkPl_    = true;
   genPl_      = true;
   rxLog_      = rogue::Logging::create("prbs.rx");
   txLog_      = rogue::Logging::create("prbs.tx");

   // Init width = 32
   width_     = 32;
   byteWidth_ = 4;
   minSize_   = 12;
   sendCount_ = false;

   // Init 4 taps
   tapCnt_  = 4;
   taps_    = (uint8_t *)malloc(sizeof(uint8_t)*tapCnt_);
   taps_[0] = 1;
   taps_[1] = 2;
   taps_[2] = 6;
   taps_[3] = 31;

   gettimeofday(&lastRxTime_,NULL);
   gettimeofday(&lastTxTime_,NULL);

   lastRxCount_ = 0;
   lastRxBytes_ = 0;
   rxRate_ = 0.0;
   rxBw_ = 0.0;

   lastTxCount_ = 0;
   lastTxBytes_ = 0;
   txRate_ = 0.0;
   txBw_ = 0.0;
}

//! Deconstructor
ru::Prbs::~Prbs() {
   free(taps_);
}

//! Compute period
double ru::Prbs::updateTime ( struct timeval *last ) {
   struct timeval cmp;
   struct timeval now;
   struct timeval per;
   double ret;

   cmp.tv_sec  = 1;
   cmp.tv_usec = 0;

   gettimeofday(&now,NULL);

   timersub(&now,last,&per);

   if ( timercmp(&per,&cmp,>) ) {
      ret = (float)per.tv_sec + (float(per.tv_usec) / 1e6);
      gettimeofday(last,NULL);
   }
   else ret = 0.0;

   return ret;
}

//! Set width
void ru::Prbs::setWidth(uint32_t width) {
   if ( width != 32 && width != 64 && width != 128 )
      throw(rogue::GeneralError("Prbs::setWidth","Invalid width."));

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lockT(pMtx_);

   width_     = width;
   byteWidth_ = width / 8;
   minSize_   = byteWidth_ * 3;
}

//! Set taps
void ru::Prbs::setTaps(uint32_t tapCnt, uint8_t * taps) {
   uint32_t i;

   boost::lock_guard<boost::mutex> lockT(pMtx_);

   free(taps_);
   tapCnt_ = tapCnt;
   taps_   = (uint8_t *)malloc(sizeof(uint8_t)*tapCnt);

   for (i=0; i < tapCnt_; i++) taps_[i] = taps[i];
}

#ifndef NO_PYTHON

//! Set taps, python
void ru::Prbs::setTapsPy(boost::python::object p) {
   Py_buffer pyBuf;

   if ( PyObject_GetBuffer(p.ptr(),&pyBuf,PyBUF_SIMPLE) < 0 ) 
      throw(rogue::GeneralError("Prbs::setTapsPy","Python Buffer Error"));

   setTaps(pyBuf.len,(uint8_t *)pyBuf.buf);
   PyBuffer_Release(&pyBuf);
}

#endif

//! Send counter value
void ru::Prbs::sendCount(bool state) {
   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lockT(pMtx_);

   sendCount_ = state;
}

void ru::Prbs::flfsr(ru::PrbsData & data) {
   bool bit = false;

   for (uint32_t x=0; x < tapCnt_; x++) bit ^= data[taps_[x]];

   data <<= 1;
   data[0] = bit;
}

//! Thread background
void ru::Prbs::runThread() {
   txLog_->logThreadId(rogue::Logging::Info);

   try {
      while(1) {
         genFrame(txSize_);
         boost::this_thread::interruption_point();
      }
   } catch (boost::thread_interrupted&) {}
}

//! Auto run data generation
void ru::Prbs::enable(uint32_t size) {

   // Verify size first
   if ((( size % byteWidth_ ) != 0) || size < minSize_ ) 
      throw rogue::GeneralError("Prbs::enable","Invalid frame size");

   if ( txThread_ == NULL ) {
      txSize_ = size;
      txThread_ = new boost::thread(boost::bind(&Prbs::runThread, this));
   }
}

//! Disable auto generation
void ru::Prbs::disable() {
   if ( txThread_ != NULL ) {
      txThread_->interrupt();
      txThread_->join();
      delete txThread_;
      txThread_ = NULL;
   }
}

//! Get RX errors
uint32_t ru::Prbs::getRxErrors() {
   return(rxErrCount_);
}

//! Get rx count
uint32_t ru::Prbs::getRxCount() {
   return(rxCount_);
}

//! Get rx bytes
uint32_t ru::Prbs::getRxBytes() {
   return(rxBytes_);
}

//! Get TX errors
uint32_t ru::Prbs::getTxErrors() {
   return(txErrCount_);
}

//! Get TX count
uint32_t ru::Prbs::getTxCount() {
   return(txCount_);
}

//! Get rx rate
double ru::Prbs::getRxRate() {
   return rxRate_;
}

//! Get rx bw
double ru::Prbs::getRxBw() {
   return rxBw_;
}

//! Get tx rate
double ru::Prbs::getTxRate() {
   return txRate_;
}

//! Get tx bw
double ru::Prbs::getTxBw() {
   return txBw_;
}

//! Get TX bytes
uint32_t ru::Prbs::getTxBytes() {
   return(txBytes_);
}

//! Set check payload flag, default = true
void ru::Prbs::checkPayload(bool state) {
   checkPl_ = state;
}

//! Set generate payload flag, default = true
void ru::Prbs::genPayload(bool state) {
   genPl_ = state;
}

//! Reset counters
// Counters should really be locked!
void ru::Prbs::resetCount() {
   pMtx_.lock();
   txErrCount_ = 0;
   txCount_    = 0;
   txBytes_    = 0;
   rxErrCount_ = 0;
   rxCount_    = 0;
   rxBytes_    = 0;
   pMtx_.unlock();
}

//! Generate a data frame
void ru::Prbs::genFrame (uint32_t size) {
   ris::Frame::iterator frIter;
   ris::Frame::iterator frEnd;
   uint32_t      frSeq[4];
   uint32_t      frSize[4];
   uint32_t      wCount[4];
   double        per;
   ris::FramePtr fr;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(pMtx_);

   // Verify size first
   if ((( size % byteWidth_ ) != 0) || size < minSize_ ) 
      throw rogue::GeneralError("Prbs::genFrame","Invalid frame size");

   // Setup size
   memset(frSize,0,16);
   frSize[0] = (size / byteWidth_) - 1;

   // Setup sequence
   memset(frSeq,0,16);
   frSeq[0]  = txSeq_;

   // Setup counter
   memset(wCount,0,16);

   // Get frame
   fr = reqFrame(size,true);

   frIter = fr->beginWrite();
   frEnd  = frIter + size;

   // First word is sequence
   ris::toFrame(frIter,byteWidth_,frSeq);
   ++wCount[0];

   // Second word is size
   ris::toFrame(frIter,byteWidth_,frSize);
   ++wCount[0];

   if ( genPl_ ) {

      // Init data
      ru::PrbsData data(byteWidth_ * 8, frSeq[0]);

      // Generate payload
      while ( frIter != frEnd ) {
         
         if ( sendCount_ ) ris::toFrame(frIter,byteWidth_,wCount);
         else {
            flfsr(data);
            to_block_range(data,frIter);
            frIter += byteWidth_;
         }
         ++wCount[0];
      }
   }

   fr->setPayload(size);
   sendFrame(fr);

   // Update counters
   txSeq_++;
   txCount_++;
   txBytes_ += size;

   if ( (per = updateTime(&lastTxTime_)) > 0.0 ) {
      txRate_ = (float)(txCount_ - lastTxCount_) / per;
      txBw_   = (float)(txBytes_ - lastTxBytes_) / per;
      lastTxCount_ = txCount_;
      lastTxBytes_ = txBytes_;
   }
}

//! Accept a frame from master
void ru::Prbs::acceptFrame ( ris::FramePtr frame ) {
   ris::Frame::iterator frIter;
   ris::Frame::iterator frEnd;
   uint32_t      frSeq[4];
   uint32_t      frSize[4];
   uint32_t      expSeq;
   uint32_t      expSize;
   uint32_t      size;
   uint32_t      pos;
   uint8_t       compData[16];
   double        per;

   rogue::GilRelease noGil;
   ris::FrameLockPtr fLock = frame->lock();
   boost::lock_guard<boost::mutex> lock(pMtx_);

   size = frame->getPayload();
   frIter = frame->beginRead();
   frEnd  = frame->endRead();

   // Verify size
   if ((( size % byteWidth_ ) != 0) || size < minSize_ ) {
      rxLog_->warning("Size violation size=%i, count=%i",size,rxCount_);
      rxErrCount_++;
      return;
   }

   // First word is sequence
   ris::fromFrame(frIter,byteWidth_,frSeq);
   expSeq = rxSeq_;
   rxSeq_ = frSeq[0] + 1;

   // Second word is size
   ris::fromFrame(frIter,byteWidth_,frSize);
   expSize = (frSize[0] + 1) * byteWidth_;

   // Check size
   if ( expSize != size ) {
      rxLog_->warning("Bad size. exp=%i, got=%i, count=%i",expSize,size,rxCount_);
      rxErrCount_++;
      return;
   }

   // Check sequence, 
   // Accept any sequence if our local count is zero
   // incoming frames with seq = 0 never cause errors and treated as a restart
   if ( frSeq[0] != 0 && expSeq != 0 && frSeq[0] != expSeq ) {
      rxLog_->warning("Bad Sequence. cur=%i, got=%i, count=%i",expSeq,frSeq[0],rxCount_);
      rxErrCount_++;
      return;
   }

   // Is payload checking enabled
   if ( checkPl_ ) {

      // Init data
      ru::PrbsData expData(byteWidth_ * 8, frSeq[0]);
      pos = 0;

      // Read payload
      while ( frIter != frEnd ) {
         flfsr(expData);
         to_block_range(expData,compData);

         if ( ! std::equal(frIter,frIter+byteWidth_,compData ) ) {
            rxLog_->warning("Bad value at index %i. count=%i, size=%i",pos,rxCount_,(size/byteWidth_)-1);
            rxErrCount_++;
            return;
         }
         frIter += byteWidth_;
         ++pos;
      }
   }

   rxCount_++;
   rxBytes_ += size;

   if ( (per = updateTime(&lastRxTime_)) > 0.0 ) {
      rxRate_ = (float)(rxCount_ - lastRxCount_) / per;
      rxBw_   = (float)(rxBytes_ - lastRxBytes_) / per;
      lastRxCount_ = rxCount_;
      lastRxBytes_ = rxBytes_;
   }
}

void ru::Prbs::setup_python() {
#ifndef NO_PYTHON

   bp::class_<ru::Prbs, ru::PrbsPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Prbs",bp::init<>())
      .def("genFrame",       &ru::Prbs::genFrame)
      .def("enable",         &ru::Prbs::enable)
      .def("disable",        &ru::Prbs::disable)
      .def("setWidth",       &ru::Prbs::setWidth)
      .def("setTaps",        &ru::Prbs::setTaps)
      .def("getRxErrors",    &ru::Prbs::getRxErrors)
      .def("getRxCount",     &ru::Prbs::getRxCount)
      .def("getRxRate",      &ru::Prbs::getRxRate)
      .def("getRxBw",        &ru::Prbs::getRxBw)
      .def("getRxBytes",     &ru::Prbs::getRxBytes)
      .def("getTxErrors",    &ru::Prbs::getTxErrors)
      .def("getTxCount",     &ru::Prbs::getTxCount)
      .def("getTxBytes",     &ru::Prbs::getTxBytes)
      .def("getTxRate",      &ru::Prbs::getTxRate)
      .def("getTxBw",        &ru::Prbs::getTxBw)
      .def("checkPayload",   &ru::Prbs::checkPayload)
      .def("genPayload",     &ru::Prbs::genPayload)
      .def("resetCount",     &ru::Prbs::resetCount)
      .def("sendCount",      &ru::Prbs::sendCount)
   ;

   bp::implicitly_convertible<ru::PrbsPtr, ris::SlavePtr>();
   bp::implicitly_convertible<ru::PrbsPtr, ris::MasterPtr>();
#endif
}


