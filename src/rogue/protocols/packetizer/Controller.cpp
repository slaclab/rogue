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
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <rogue/protocols/packetizer/Controller.h>
#include <rogue/protocols/packetizer/Transport.h>
#include <rogue/protocols/packetizer/Application.h>
#include <rogue/GeneralError.h>
#include <rogue/Helpers.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <math.h>

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;

//! Creator
rpp::Controller::Controller ( rpp::TransportPtr tran, rpp::ApplicationPtr * app,
                              uint32_t headSize, uint32_t tailSize, uint32_t alignSize, bool enSsi ) {
   uint32_t x;

   enSsi_ = enSsi;
   app_   = app;
   tran_  = tran;
   appIndex_ = 0;
   tranIndex_ = 0;
   tranDest_ = 0;
   dropCount_ = 0;
   tranQueue_.setThold(64);
   log_ = rogue::Logging::create("packetizer.Controller");

   rogue::defaultTimeout(timeout_);

   headSize_ = headSize;
   tailSize_ = tailSize;
   alignSize_ = alignSize;

   for ( x=0; x < 256; x++ ) {
         transSof_[x]  = true;
         crc_[x]       = 0;
         tranCount_[x] = 0;
   }
}

//! Destructor
rpp::Controller::~Controller() {
   this->stopQueue();
}

//! Stop TX
void rpp::Controller::stopQueue() {
   rogue::GilRelease noGil;
   tranQueue_.stop();
}

//! Transport frame allocation request
// Needs to be updated to support cascaded packetizers
ris::FramePtr rpp::Controller::reqFrame ( uint32_t size ) {
   ris::FramePtr  lFrame;
   ris::FramePtr  rFrame;
   ris::BufferPtr buff;
   uint32_t fSize;

   // Create frame container for request response
   lFrame = ris::Frame::create();

   // Align total size to configured alignment
   if ( (size % alignSize_) != 0 ) size += (alignSize_-(size % alignSize_));

   // Request individual frames upstream
   while ( lFrame->getAvailable() < size ) {

      // Generate a new size with header and tail
      fSize = (size - lFrame->getAvailable()) + headSize_ + tailSize_;

      // Pass request
      rFrame = tran_->reqFrame (fSize, false);

      // Take only the first buffer. This will break a cascaded packetizer
      // system. We need to fix this!
      buff = *(rFrame->beginBuffer());

      // Use buffer tail reservation to align available payload
      if (((buff->getAvailable()-tailSize_) % alignSize_) != 0)
         buff->adjustTail((buff->getAvailable()-tailSize_) % alignSize_);

      // Buffer should support our header/tail plus at least one payload byte
      if ( buff->getAvailable() < (headSize_ + tailSize_ + 1) )
         throw(rogue::GeneralError::create("packetizer::Controller::reqFrame",
                  "Buffer size %i is less than min size required %i",
                  buff->getAvailable(), (headSize_ + tailSize_ + 1)));

      // Add 8 bytes to head and tail reservation
      buff->adjustHeader(headSize_);
      buff->adjustTail(tailSize_);

      // Add buffer to return frame
      lFrame->appendBuffer(buff);
   }
   return(lFrame);
}

//! Frame received at transport interface
void rpp::Controller::transportRx( ris::FramePtr frame ) {}

//! Frame transmit at transport interface
// Called by transport class thread
ris::FramePtr rpp::Controller::transportTx() {
   ris::FramePtr frame;
   frame = tranQueue_.pop();
   return(frame);
}

//! Frame received at application interface
void rpp::Controller::applicationRx ( ris::FramePtr frame, uint8_t tDest ) { }

//! Get drop count
uint32_t rpp::Controller::getDropCount() {
   return(dropCount_);
}

//! Set timeout for frame transmits in microseconds
void rpp::Controller::setTimeout(uint32_t timeout) {
   div_t divResult = div(timeout,1000000);
   timeout_.tv_sec  = divResult.quot;
   timeout_.tv_usec = divResult.rem;
}

