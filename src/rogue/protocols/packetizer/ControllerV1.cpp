/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Controller Version 1
 * ----------------------------------------------------------------------------
 * File       : ControllerV1.cpp
 * Created    : 2018-02-02
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller V1
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
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/protocols/packetizer/ControllerV1.h>
#include <rogue/protocols/packetizer/Transport.h>
#include <rogue/protocols/packetizer/Application.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <math.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/time.h>

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;

//! Class creation
rpp::ControllerV1Ptr rpp::ControllerV1::create (bool enSsi, rpp::TransportPtr tran, rpp::ApplicationPtr * app ) {
   rpp::ControllerV1Ptr r = std::make_shared<rpp::ControllerV1>(enSsi,tran,app);
   return(r);
}

//! Creator
rpp::ControllerV1::ControllerV1 (bool enSsi, rpp::TransportPtr tran, rpp::ApplicationPtr * app ) : rpp::Controller::Controller(tran, app, 8, 1, 8, enSsi) {
}

//! Destructor
rpp::ControllerV1::~ControllerV1() { }

//! Frame received at transport interface
void rpp::ControllerV1::transportRx( ris::FramePtr frame ) {
   ris::BufferPtr buff;
   uint32_t  size;
   uint32_t  tmpIdx;
   uint32_t  tmpCount;
   uint8_t   tmpFuser;
   uint8_t   tmpLuser;
   uint8_t   tmpDest;
   uint8_t   tmpId;
   bool      tmpEof;
   uint32_t  flags;
   uint8_t * data;

   if ( frame->isEmpty() )
      log_->warning("Empty frame received At Transport");

   rogue::GilRelease noGil;
   ris::FrameLockPtr flock = frame->lock();
   std::lock_guard<std::mutex> lock(tranMtx_);

   buff = *(frame->beginBuffer());
   data = buff->begin();
   size = buff->getPayload();

   // Drop invalid data
   if ( frame->getError() ||           // Check for frame ERROR
      ( frame->bufferCount() != 1 ) || // Incoming frame can only have one buffer
      (size < 10) ||                   // Check for min. size (64-bit header + 8-bit min. payload + 8-bit tail)
      ((data[0] & 0xF) != 0) ) {       // Check for invalid version only
      log_->warning("Dropping frame due to contents: error=0x%x, payload=%i, buffers=%i, Version=0x%x",frame->getError(),size,frame->bufferCount(),data[0]&0xF);
      dropCount_++;
      return;
   }

   tmpIdx  = uint32_t(data[0]) >> 4;
   tmpIdx |= uint32_t(data[1]) << 4;

   tmpCount  = uint32_t(data[2]);
   tmpCount |= uint32_t(data[3]) << 8;
   tmpCount |= uint32_t(data[4]) << 16;

   tmpDest  = data[5];
   tmpId    = data[6];
   tmpFuser = data[7];

   tmpLuser = data[size-1] & 0x7F;
   tmpEof   = data[size-1] & 0x80;

   log_->debug("transportRx: Raw header: 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x, 0x%x",
         data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7]);
   log_->debug("transportRx: Raw footer: 0x%x",
         data[size-1]);
   log_->debug("transportRx: Got frame: Fuser=0x%x, Dest=0x%x, Id=0x%x, Count=%i, Luser=0x%x, Eof=%i, size=%i",
         tmpFuser, tmpDest, tmpIdx, tmpCount, tmpLuser, tmpEof, size);

   // Shorten message by one byte (before adjusting tail)
   buff->adjustPayload(-1);

   // Adjust header and tail reservations
   buff->adjustHeader(8);
   buff->adjustTail(1);

   // Drop frame and reset state if mismatch
   if ( tmpCount > 0  && ( tmpIdx != tranIndex_ || tmpCount != tranCount_[0] ) ) {
      log_->warning("Dropping frame due to state mismatch: expIdx=%i, gotIdx=%i, expCount=%i, gotCount=%i",tranIndex_,tmpIdx,tranCount_[0],tmpCount);
      dropCount_++;
      tranCount_[0] = 0;
      tranFrame_[0].reset();
      return;
   }

   // First frame
   if ( tmpCount == 0 ) {

      if ( tranCount_[0] != 0 )
         log_->warning("Dropping frame due to new incoming frame: expIdx=%i, expCount=%i",tranIndex_,tranCount_[0]);

      tranFrame_[0] = ris::Frame::create();
      tranIndex_    = tmpIdx;
      tranDest_     = tmpDest;
      tranCount_[0] = 0;

      tranFrame_[0]->setFirstUser(tmpFuser);
   }

   tranFrame_[0]->appendBuffer(buff);
   frame->clear(); // Empty old frame

   // Last of transfer
   if ( tmpEof ) {
      tranFrame_[0]->setLastUser(tmpLuser);
      tranCount_[0] = 0;
      if ( app_[tranDest_] ) {
         app_[tranDest_]->pushFrame(tranFrame_[0]);
      }
      tranFrame_[0].reset();

      // Detect SSI error
      if ( enSsi_ & (tmpLuser & 0x1) ) tranFrame_[tmpDest]->setError(0x80);
   }
   else tranCount_[0]++;
}

//! Frame received at application interface
void rpp::ControllerV1::applicationRx ( ris::FramePtr frame, uint8_t tDest ) {
   ris::Frame::BufferIterator it;
   uint32_t segment;
   uint8_t * data;
   uint32_t size;
   uint8_t  fUser;
   uint8_t  lUser;
   struct timeval startTime;
   struct timeval currTime;
   struct timeval endTime;

   gettimeofday(&startTime,NULL);
   timeradd(&startTime,&timeout_,&endTime);

   if ( frame->isEmpty() )
      log_->warning("Empty frame received at application");

   if ( frame->getError() ) return;

   rogue::GilRelease noGil;
   ris::FrameLockPtr flock = frame->lock();
   std::lock_guard<std::mutex> lock(appMtx_);

   // Wait while queue is busy
   while ( tranQueue_.busy() ) {
      usleep(10);
      gettimeofday(&currTime,NULL);
      if ( timercmp(&currTime,&endTime,>)) {
         log_->critical("ControllerV1::applicationRx: Timeout waiting for outbound queue after %i.%i seconds! May be caused by outbound backpressure.", timeout_.tv_sec, timeout_.tv_usec);
         gettimeofday(&startTime,NULL);
         timeradd(&startTime,&timeout_,&endTime);
      }
   }

   // User fields
   fUser = frame->getFirstUser();
   lUser = frame->getLastUser();

   // Inject SOF
   if ( enSsi_ ) fUser |= 0x2;

   segment = 0;
   for (it=frame->beginBuffer(); it != frame->endBuffer(); ++it) {
      ris::FramePtr tFrame = ris::Frame::create();

      // Adjust header and tail, before setting new size
      (*it)->adjustHeader(-8);
      (*it)->adjustTail(-1);

      // Make payload one byte longer
      (*it)->adjustPayload(1);

      size = (*it)->getPayload();
      data = (*it)->begin();

      data[0] = (appIndex_ & 0xF) << 4; // Note: BIT3:0 = 0x0 (Version)
      data[1] = (appIndex_ >> 4)  & 0xFF;

      data[2] = (segment >> 0)  & 0xFF;
      data[3] = (segment >> 8)  & 0xFF;
      data[4] = (segment >> 16) & 0xFF;

      data[5] = tDest;
      data[6] = 0; // TID Unused
      data[7] = fUser;

      data[size-1] = lUser & 0x7F;

      if ( it == (frame->endBuffer()-1) ) data[size-1] |= 0x80;

      tFrame->appendBuffer(*it);
      tranQueue_.push(tFrame);
      segment++;
   }
   appIndex_++;
   frame->clear(); // Empty old frame
}

