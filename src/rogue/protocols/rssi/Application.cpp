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
#include <rogue/protocols/rssi/Controller.h>
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

void rpr::Application::setup_python() {

   bp::class_<rpr::Application, rpr::ApplicationPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Application",bp::init<>())
      .def("create",         &rpr::Application::create)
      .staticmethod("create")
   ;

   bp::implicitly_convertible<rpr::ApplicationPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpr::ApplicationPtr, ris::SlavePtr>();
}

//! Creator
rpr::Application::Application () { }

//! Destructor
rpr::Application::~Application() { }

//! Setup links
void rpr::Application::setController( rpr::ControllerPtr cntl ) {
   cntl_ = cntl;
}

//! Generate a Frame. Called from master
ris::FramePtr rpr::Application::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize ) {
   return(cntl_->reqFrame(size,maxBuffSize));
}

//! Accept a frame from master
void rpr::Application::acceptFrame ( ris::FramePtr frame ) {
   cntl_->transportRx(frame);
}

