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
rpr::ControllerPtr rpr::Controller::create ( rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>(tran,app);
   return(r);
}

void rpr::Controller::setup_python() {
   // Nothing to do
}

//! Creator
rpr::Controller::Controller ( rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
   app_  = app;
   tran_ = tran;
}

//! Destructor
rpr::Controller::~Controller() { }

//! Transport frame allocation request
ris::FramePtr rpr::Controller::reqFrame ( uint32_t size, uint32_t maxBuffSize ) {
   ris::FramePtr frame;
   uint32_t      nSize;
   uint32_t      bSize;
#if 0
   // Determine buffer size
   if ( maxBuffSize > remMaxSegment_ ) bSize = remMaxSegment_;
   else bSize = maxBuffSize;

   // Adjust request size to include our header
   nSize = size + rpr::Header::HeaderSize;

   // Forward frame request to transport slave
   frame = tran_->reqFrame (nSize, false, bSize);

   // Make sure there is enough room in first buffer for our header
   if ( frame->getBuffer(0)->getAvailable() < rpr::Header::HeaderSize )
      throw(rogue::GeneralError::boundary("Controller::reqFrame",
                                          rpr::Header::HeaderSize,
                                          frame->getBuffer(0)->getAvailable()));

   // Update first buffer to include our header space.
   frame->getBuffer(0)->setHeadRoom(frame->getBuffer(0)->getHeadRoom() + rpr::Header::HeaderSize);
#endif
   // Return frame
   return(frame);
}

//! Frame received at transport interface
void rpr::Controller::transportRx( ris::FramePtr frame ) {

}

//! Frame received at application interface
void rpr::Controller::applicationRx ( ris::FramePtr frame ) {

////   PyRogue_BEGIN_ALLOW_THREADS;
////   {
////      boost::unique_lock<boost::mutex> lock(mtx_);

////   }
////   PyRogue_END_ALLOW_THREADS;

}

