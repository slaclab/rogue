/**
 *-----------------------------------------------------------------------------
 * Title      : RSSI Controller
 * ----------------------------------------------------------------------------
 * File       : Controller.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Controller
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
rpr::ControllerPtr rpr::Controller::create () {
   rpr::ControllerPtr r = boost::make_shared<rpr::Controller>();
   return(r);
}

//! Creator
rpr::Controller::Controller () { }

//! Destructor
rpr::Controller::~Controller() { }

//! Setup links
void rpr::Controller::setup( rpr::TransportPtr tran, rpr::ApplicationPtr app ) {
   app_  = app;
   tran_ = tran;
}

//! Frame received at transport interface
void rpr::Controller::transportRx( ris::FramePtr frame ) {



}

//! Frame received at application interface
void rpr::Controller::applicationRx( ris::FramePtr frame ) {



}

//! Background thread
void rpr::Controller::runThread() {


}

