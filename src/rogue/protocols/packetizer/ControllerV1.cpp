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
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/protocols/packetizer/ControllerV1.h>
#include <rogue/protocols/packetizer/Transport.h>
#include <rogue/protocols/packetizer/Application.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <boost/pointer_cast.hpp>
#include <rogue/GilRelease.h>
#include <math.h>

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpp::ControllerV1Ptr rpp::ControllerV1::create ( rpp::TransportPtr tran, rpp::ApplicationPtr * app ) {
   rpp::ControllerV1Ptr r = boost::make_shared<rpp::ControllerV1>(tran,app);
   return(r);
}

//! Creator
rpp::ControllerV1::ControllerV1 ( rpp::TransportPtr tran, rpp::ApplicationPtr * app ) : rpp::Controller::Controller(tran, app, 8, 1, 1) {
}

//! Destructor
rpp::ControllerV1::~ControllerV1() { }

//! Frame received at transport interface
void rpp::ControllerV1::transportRx( ris::FramePtr frame ) {
   ris::BufferPtr buff;
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
   boost::lock_guard<boost::mutex> lock(tranMtx_);

   buff = *(frame->beginBuffer());
   data = buff->begin();

   // Drop invalid data
   if ( frame->getError() || (buff->getPayload() < 9) || ((data[0] & 0xF) != 0) ) {
      log_->warning("Dropping frame due to contents: error=0x%x, payload=%i, Version=0x%x",frame->getError(),buff->getPayload(),data[0]&0xF);
      dropCount_++;
      return;
   }

   tmpIdx  = (data[0] >> 4);
   tmpIdx += data[1] * 16;

   tmpCount  = data[2];
   tmpCount += data[3] * 256;
   tmpCount += data[4] * 0x10000;

   tmpDest  = data[5];
   tmpId    = data[6];
   tmpFuser = data[7];

   tmpLuser = data[buff->getPayload()-1] & 0x7F;
   tmpEof   = data[buff->getPayload()-1] & 0x80;

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

      flags  = tmpFuser;
      if ( tmpEof ) flags += tmpLuser << 8;
      flags += tmpId   << 16;
      flags += tmpDest << 24;
      tranFrame_[0]->setFlags(flags);
   }

   tranFrame_[0]->appendBuffer(buff);
   //frame->clear();

   // Last of transfer
   if ( tmpEof ) {
      flags = tranFrame_[0]->getFlags() & 0xFFFF00FF;
      flags += tmpLuser << 8;
      tranFrame_[0]->setFlags(flags);

      tranCount_[0] = 0;
      if ( app_[tranDest_] ) {
         app_[tranDest_]->pushFrame(tranFrame_[0]);
      }
      tranFrame_[0].reset();
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
   uint8_t  tId;
   struct timeval startTime;
   struct timeval currTime;
   struct timeval sumTime;
   struct timeval endTime;

   if ( timeout_ > 0 ) {
      gettimeofday(&startTime,NULL);
      sumTime.tv_sec = (timeout_ / 1000000);
      sumTime.tv_usec = (timeout_ % 1000000);
      timeradd(&startTime,&sumTime,&endTime);
   }
   else gettimeofday(&endTime,NULL);

   if ( frame->isEmpty() ) 
      log_->warning("Empty frame received at application");

   if ( frame->getError() ) return;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(appMtx_);

   // Wait while queue is busy
   while ( tranQueue_.busy() ) {
      usleep(10);
      if ( timeout_ > 0 ) {
         gettimeofday(&currTime,NULL);
         if ( timercmp(&currTime,&endTime,>))
            throw(rogue::GeneralError::timeout("packetizer::ControllerV1::applicationRx",timeout_));
      }
   }

   fUser = frame->getFlags() & 0xFF;
   lUser = (frame->getFlags() >> 8) & 0xFF;
   tId   = (frame->getFlags() >> 16) & 0xFF;

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

      data[0] = ((appIndex_ % 16) << 4);
      data[1] = (appIndex_ / 16) & 0xFF;

      data[2] = segment % 256;
      data[3] = (segment % 0xFFFF) / 256;
      data[4] = segment / 0xFFFF;

      data[5] = tDest;
      data[6] = tId;
      data[7] = fUser;

      data[size-1] = lUser & 0x7F;

      if ( it == (frame->endBuffer()-1) ) data[size-1] |= 0x80;

      tFrame->appendBuffer(*it);
      tranQueue_.push(tFrame);
      segment++;
   }
   appIndex_++;
   //frame->clear();
}

