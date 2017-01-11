/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Transport Port
 * ----------------------------------------------------------------------------
 * File       : Transport.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Transport Port
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
#include <rogue/protocols/rssi/Controller.h>
#include <rogue/protocols/rssi/Transport.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpr::TransportPtr rpr::Transport::create () {
   rpr::TransportPtr r = boost::make_shared<rpr::Transport>();
   return(r);
}

//! Creator
rpr::Transport::Transport () { }

//! Destructor
rpr::Transport::~Transport() { }

//! Setup links
void rpr::Transport::setController( rpr::ControllerPtr cntl ) {
   cntl_ = cntl;
}

//! Generate a Frame. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 * maxBuffSize indicates the largest acceptable buffer size. A larger buffer can be
 * returned but the total buffer count must assume each buffer is of size maxBuffSize
 * If maxBuffSize = 0, slave will freely determine the buffer size.
 */
ris::FramePtr rpr::Transport::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize ) {
   throw(rogue::GeneralError("Transport::acceptReq","Invalid frame request."));
}

//! Accept a frame from master
void rpr::Transport::acceptFrame ( ris::FramePtr frame ) {
   cntl_->applicationRx(frame);
}

