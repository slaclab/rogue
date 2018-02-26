/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Controller
 * ----------------------------------------------------------------------------
 * File       : Controller.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Controller
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
#include <rogue/protocols/packetizer/Controller.h>
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
rpp::ControllerPtr rpp::Controller::create ( uint32_t segmentSize, 
                                             rpp::TransportPtr tran, rpp::ApplicationPtr * app ) {
   rpp::ControllerPtr r = boost::make_shared<rpp::Controller>(segmentSize,tran,app);
   return(r);
}

void rpp::Controller::setup_python() {
   // Nothing to do
}

//! Creator
rpp::Controller::Controller ( uint32_t segmentSize, rpp::TransportPtr tran, rpp::ApplicationPtr * app ) {
   app_  = app;
   tran_ = tran;
   segmentSize_ = segmentSize;
   appIndex_ = 0;
   tranIndex_ = 0;
   tranCount_ = 0;
   tranDest_ = 0;
   dropCount_ = 0;
   timeout_ = 1000000;
   tranQueue_.setThold(64);
   log_ = new rogue::Logging("packetizer.Controller");
}

//! Destructor
rpp::Controller::~Controller() { }

//! Transport frame allocation request
ris::FramePtr rpp::Controller::reqFrame ( uint32_t size ) {
   ris::FramePtr  lFrame;
   ris::FramePtr  rFrame;
   ris::BufferPtr buff;

   // Create frame container for request response
   lFrame = ris::Frame::create();

   // Request individual frames upstream with buffer = segmentSize_
   while ( lFrame->getAvailable() < size ) {
      rFrame = tran_->reqFrame (segmentSize_, false);
      buff = rFrame->getBuffer(0);
  
      // Buffer should support our header/tail plus at least one payload byte 
      if ( buff->getAvailable() < 10 )
         throw(rogue::GeneralError::boundary("packetizer::Controller::reqFrame",10,
                                             buff->getAvailable()));

      // Add 8 bytes to headroom
      buff->setHeadRoom(buff->getHeadRoom() + 8);
      
      // Add buffer to return frame
      lFrame->appendBuffer(buff);
   }

   return(lFrame);
}

//! Frame received at transport interface
void rpp::Controller::transportRx( ris::FramePtr frame ) {
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

   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("packetizer::Controller::transportRx","Frame must not be empty"));

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(tranMtx_);

   buff = frame->getBuffer(0);
   data = buff->getPayloadData();

   // Drop invalid data
   if ( frame->getError() || (buff->getPayload() < 9) || ((data[0] & 0xF) != 0) ) {
      log_->info("Dropping frame due to contents: error=0x%x, payload=%i, Version=0x%x",frame->getError(),buff->getPayload(),data[0]&0xF);
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

   // Rem 8 bytes to headroom
   buff->setHeadRoom(buff->getHeadRoom() + 8);

   // Shorten message by one byte
   buff->setPayload(buff->getPayload()-1);

   // Drop frame and reset state if mismatch
   if ( tmpCount > 0  && ( tmpIdx != tranIndex_ || tmpCount != tranCount_ ) ) {
      log_->info("Dropping frame due to state mismatch: expIdx=%i, gotIdx=%i, expCount=%i, gotCount=%i",tranIndex_,tmpIdx,tranCount_,tmpCount);
      dropCount_++;
      tranCount_ = 0;
      tranFrame_.reset();
      return;
   }

   // First frame
   if ( tmpCount == 0 ) {

      if ( tranCount_ != 0 ) 
         log_->info("Dropping frame due to new incoming frame: expIdx=%i, expCount=%i",tranIndex_,tranCount_);

      tranFrame_ = ris::Frame::create();
      tranIndex_ = tmpIdx;
      tranDest_  = tmpDest;
      tranCount_ = 0;

      flags  = tmpFuser;
      if ( tmpEof ) flags += tmpLuser << 8;
      flags += tmpId   << 16;
      flags += tmpDest << 24;
      frame->setFlags(flags);
   }

   tranFrame_->appendBuffer(buff);

   // Last of transfer
   if ( tmpEof ) {
      tranCount_ = 0;
      if ( app_[tranDest_] ) {
         app_[tranDest_]->pushFrame(tranFrame_);
      }
      tranFrame_.reset();
   }
   else tranCount_++;
}

//! Frame transmit at transport interface
// Called by transport class thread
ris::FramePtr rpp::Controller::transportTx() {
   ris::FramePtr frame;
   frame = tranQueue_.pop();
   return(frame);
}

//! Frame received at application interface
void rpp::Controller::applicationRx ( ris::FramePtr frame, uint8_t tDest ) {
   ris::BufferPtr buff;
   uint8_t * data;
   uint32_t x;
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

   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("packetizer::Controller::applicationRx","Frame must not be empty"));

   if ( frame->getError() ) return;

   rogue::GilRelease noGil;
   boost::lock_guard<boost::mutex> lock(appMtx_);

   // Wait while queue is busy
   while ( tranQueue_.busy() ) {
      usleep(10);
      if ( timeout_ > 0 ) {
         gettimeofday(&currTime,NULL);
         if ( timercmp(&currTime,&endTime,>))
            throw(rogue::GeneralError::timeout("packetizer::Controller::applicationRx",timeout_));
      }
   }

   fUser = frame->getFlags() & 0xFF;
   lUser = (frame->getFlags() >> 8) & 0xFF;
   tId   = (frame->getFlags() >> 16) & 0xFF;

   for (x=0; x < frame->getCount(); x++ ) {
      ris::FramePtr tFrame = ris::Frame::create();
      buff = frame->getBuffer(x);

      // Rem 8 bytes to headroom
      buff->setHeadRoom(buff->getHeadRoom() - 8);
      
      // Make payload one byte longer
      buff->setPayload(buff->getPayload()+1);

      size = buff->getPayload();
      data = buff->getPayloadData();

      data[0] = ((appIndex_ % 16) << 4);
      data[1] = (appIndex_ / 16) & 0xFF;

      data[2] = x % 256;
      data[3] = (x % 0xFFFF) / 256;
      data[4] = x / 0xFFFF;

      data[5] = tDest;
      data[6] = tId;
      data[7] = fUser;

      data[size-1] = lUser & 0x7F;

      if ( x == (frame->getCount()-1) ) data[size-1] |= 0x80;

      tFrame->appendBuffer(buff);
      tranQueue_.push(tFrame);
   }
   appIndex_++;
}

//! Get drop count
uint32_t rpp::Controller::getDropCount() {
   return(dropCount_);
}

//! Set timeout for frame transmits in microseconds
void rpp::Controller::setTimeout(uint32_t timeout) {
    timeout_ = timeout;
}

