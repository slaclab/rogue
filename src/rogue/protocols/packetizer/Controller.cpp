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
#include <rogue/common.h>
#include <math.h>

namespace rpr = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::ControllerPtr rpr::Controller::create ( uint32_t segmentSize, 
                                             rpr::TransportPtr tran, rpr::ApplicationPtr * app ) {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>(segmentSize,tran,app);
   return(r);
}

void rpr::Controller::setup_python() {
   // Nothing to do
}

//! Creator
rpr::Controller::Controller ( uint32_t segmentSize, rpr::TransportPtr tran, rpr::ApplicationPtr * app ) {
   app_  = app;
   tran_ = tran;
   segmentSize_ = segmentSize;
   appIndex_ = 0;
   tranIndex_ = 0;
   tranCount_ = 0;
   tranDest_ = 0;
}

//! Destructor
rpr::Controller::~Controller() { }

//! Transport frame allocation request
ris::FramePtr rpr::Controller::reqFrame ( uint32_t size, uint32_t maxBuffSize ) {
   ris::FramePtr  lFrame;
   ris::FramePtr  rFrame;
   ris::BufferPtr buff;

   // Create frame container for request response
   lFrame = ris::Frame::create();

   // Request individual frames upstream with buffer = segmentSize_
   while ( lFrame->getAvailable() < size ) {
      rFrame = tran_->reqFrame (segmentSize_, false, segmentSize_);
      buff = rFrame->getBuffer(0);
   
      // Make sure there is enough room in first buffer for our header/tail plus size
      if ( buff->getAvailable() < ( segmentSize_ + 9) )
         throw(rogue::GeneralError::boundary("Controller::reqFrame",
                                             (segmentSize_ + 9), buff->getAvailable()));

      // Add 8 bytes to headroom
      buff->setHeadRoom(buff->getHeadRoom() + 8);
      
      // Add 1 bytes to tailroom
      buff->setTailRoom(buff->getTailRoom() + 1);

      // Add buffer to return frame
      lFrame->appendBuffer(buff);
   }

   return(lFrame);
}

//! Frame received at transport interface
void rpr::Controller::transportRx( ris::FramePtr frame ) {
   ris::FramePtr tFrame;
   ris::BufferPtr buff;
   ris::MasterPtr mast;
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
      throw(rogue::GeneralError("Controller::transportRx","Frame must not be empty"));

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(tranMtx_);

      buff = frame->getBuffer(0);
      data = buff->getPayloadData();

      // Drop invalid data
      if ( frame->getError() || (buff->getPayload() < 9) || ((data[0] & 0xF) != 0) ) return;

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
      
      // Rem 1 bytes to tailroom
      buff->setTailRoom(buff->getTailRoom() + 1);

      // Drop frame and reset state if mismatch
      if ( tranCount_ > 0  && ( tmpIdx != tranIndex_ || tmpCount != tranCount_ ) ) {
         tranCount_ = 0;
         tranFrame_.reset();
         return;
      }

      // First frame
      if ( tranCount_ == 0 ) {
         tranFrame_ = ris::Frame::create();
         tranIndex_ = tmpIdx;
         tranDest_  = tmpDest;

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
            tFrame = tranFrame_;
            mast = app_[tranDest_];
         }
         tranFrame_.reset();
      }
   }
   PyRogue_END_ALLOW_THREADS;

   if ( tFrame ) mast->sendFrame(tFrame);
}

//! Frame received at application interface
void rpr::Controller::applicationRx ( ris::FramePtr frame, uint8_t tDest ) {
   ris::BufferPtr buff;
   uint8_t * data;
   uint32_t x;
   uint32_t size;
   uint8_t  fUser;
   uint8_t  lUser;
   uint8_t  tId;

   if ( frame->getCount() == 0 ) 
      throw(rogue::GeneralError("Controller::applicationRx","Frame must not be empty"));

   if ( frame->getError() ) return;

   PyRogue_BEGIN_ALLOW_THREADS;
   {
      boost::lock_guard<boost::mutex> lock(appMtx_);

      fUser = frame->getFlags() & 0xFF;
      lUser = (frame->getFlags() >> 8) & 0xFF;
      tId   = (frame->getFlags() >> 16) & 0xFF;

      for (x=0; x < frame->getCount(); x++ ) {
         ris::FramePtr tFrame = ris::Frame::create();
         
         buff = frame->getBuffer(x);
         size = buff->getPayload();

         // Rem 8 bytes to headroom
         buff->setHeadRoom(buff->getHeadRoom() - 8);
         
         // Rem 1 bytes to tailroom
         buff->setTailRoom(buff->getTailRoom() - 1);

         data = buff->getPayloadData();

         data[0] = appIndex_ % 16;
         data[1] = appIndex_ / 16;
         appIndex_++;

         data[2] = x % 256;
         data[3] = (x % 0xFFFF) / 256;
         data[4] = x / 0xFFFF;

         data[5] = tDest;
         data[6] = tId;
         data[7] = fUser;

         data[size+8] = lUser & 0x7F;

         if ( x == frame->getCount()-1 ) data[size+8] |= 0x80;

         tFrame->appendBuffer(buff);

         // Nested lock will occur here. May need to create queue & tx thread to fix
         tran_->sendFrame(tFrame);
      }
   }
   PyRogue_END_ALLOW_THREADS;
}

