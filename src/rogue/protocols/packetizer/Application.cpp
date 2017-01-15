/**
 *-----------------------------------------------------------------------------
 * Title      : Packetizer Application Port
 * ----------------------------------------------------------------------------
 * File       : Application.h
 * Created    : 2017-01-07
 * Last update: 2017-01-07
 * ----------------------------------------------------------------------------
 * Description:
 * Packetizer Application Port
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
#include <rogue/protocols/packetizer/Application.h>
#include <rogue/GeneralError.h>
#include <boost/make_shared.hpp>
#include <rogue/common.h>

namespace rpp = rogue::protocols::packetizer;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rpp::ApplicationPtr rpp::Application::create (uint8_t id) {
   rpp::ApplicationPtr r = boost::make_shared<rpp::Application>(id);
   return(r);
}

void rpp::Application::setup_python() {

   bp::class_<rpp::Application, rpp::ApplicationPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Application",bp::init<uint8_t>())
      .def("create",         &rpp::Application::create)
      .staticmethod("create")
   ;

   bp::implicitly_convertible<rpp::ApplicationPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpp::ApplicationPtr, ris::SlavePtr>();
}

//! Creator
rpp::Application::Application (uint8_t id) { 
   id_ = id;
}

//! Destructor
rpp::Application::~Application() { }

//! Setup links
void rpp::Application::setController( rpp::ControllerPtr cntl ) {
   cntl_ = cntl;
}

//! Generate a Frame. Called from master
ris::FramePtr rpp::Application::acceptReq ( uint32_t size, bool zeroCopyEn, uint32_t maxBuffSize ) {
   return(cntl_->reqFrame(size,maxBuffSize));
}

//! Accept a frame from master
void rpp::Application::acceptFrame ( ris::FramePtr frame ) {
   cntl_->applicationRx(frame,id_);
}

