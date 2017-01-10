/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Application Port
 * ----------------------------------------------------------------------------
 * File       : Application.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Application Port
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
#include <rogue/protocols/rssi/Header.h>
#include <rogue/protocols/rssi/Controller.h>
#include <rogue/protocols/rssi/Transport.h>
#include <rogue/protocols/rssi/Application.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::ApplicationPtr rpr::Application::create () {
   rpr::ApplicationPtr r = boost::make_shared<rpr::Application>();
   return(r);
}

//! Creator
rpr::Application::Application () { }

//! Destructor
rpr::Application::~Application() { }

//! Setup links
void rpr::Application::setup( rpr::ControllerPtr cntl, rpr::TransportPtr tran ) {
   cntl_ = cntl;
   tran_ = tran;
}

//! Generate a Frame. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 * maxBuffSize indicates the largest acceptable buffer size. A larger buffer can be
 * returned but the total buffer count must assume each buffer is of size maxBuffSize
 * If maxBuffSize = 0, slave will freely determine the buffer size.
 */
ris::FramePtr rpr::Application::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize ) {
   uint32_t      nsize;
   ris::FramePtr frame;
   uint32_t      x;

   // Add header to frame size
   nsize = size + rpr::Header::minSize();

   // Forward frame request to transport slave
   frame = tran_->reqFrame (nsize, zeroCopyEn, maxBuffSize);

   // Update header area in each buffer before returning frame
   for (x=0; x < frame->getCount(); x++) 
      frame->getBuffer(x)->setHeadRoom(frame->getBuffer(x)->getHeadRoom() + rpr::Header::minSize());

   // Return frame
   return(frame);
}

//! Accept a frame from master
void rpr::Application::acceptFrame ( ris::FramePtr frame ) {
   cntl_->transportRx(frame);
}

