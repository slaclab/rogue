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

void rpp::Controller::setup_python() {
   // Nothing to do
}

//! Creator
rpp::Controller::Controller ( uint32_t segmentSize, rpp::TransportPtr tran, rpp::ApplicationPtr * app,
                              uint32_t headSize, uint32_t tailSize ) {
   uint32_t x;

   app_  = app;
   tran_ = tran;
   segmentSize_ = segmentSize;
   appIndex_ = 0;
   tranIndex_ = 0;
   tranDest_ = 0;
   dropCount_ = 0;
   timeout_ = 1000000;
   tranQueue_.setThold(64);
   log_ = new rogue::Logging("packetizer.Controller");

   headSize_ = headSize;
   tailSize_ = tailSize;

   for ( x=0; x < 256; x++ ) {
         transSof_[x]  = true;
         crcInit_[x]   = 0xFFFFFFFF;
         tranCount_[x] = 0;
   }
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
      if ( buff->getAvailable() < (headSize_ + tailSize_ + 1) )
         throw(rogue::GeneralError::boundary("packetizer::Controller::reqFrame",
                  (headSize_ + tailSize_ + 1), buff->getAvailable()));

      // Add 8 bytes to headroom
      buff->setHeadRoom(buff->getHeadRoom() + headSize_);
      buff->setTailRoom(buff->getTailRoom() + tailSize_);

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
    timeout_ = timeout;
}

