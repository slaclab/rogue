/**
 *-----------------------------------------------------------------------------
 * Title      : XVC Server Wrapper  Class
 * ----------------------------------------------------------------------------
 * File       : Xvc.h
 * Created    : 2022-03-23
 * Last update: 2022-03-23
 * ----------------------------------------------------------------------------
 * Description:
 * XVC Server Wrapper Class
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
#include <rogue/protocols/xilinx/xvc/Xvc.h>
#include <rogue/GeneralError.h>
#include <memory>
#include <rogue/GilRelease.h>
#include <rogue/Logging.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

namespace rpxx = rogue::protocols::xilinx::xvc;
namespace ris  = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rpxx::XvcPtr rpxx::Xvc::create (std::string host, uint16_t port) {
   rpxx::XvcPtr r = std::make_shared<rpxx::Xvc>(host,port);
   return(r);
}

//! Creator
rpxx::Xvc::Xvc ( std::string host, uint16_t port) {

}

//! Destructor
rpxx::Xvc::~Xvc() {

}

void rpxx::Xvc::setup_python () {
#ifndef NO_PYTHON

   bp::class_<rpxx::Xvc, rpxx::XvcPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Xvc",bp::init<std::string,uint16_t>());

   bp::implicitly_convertible<rpxx::XvcPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpxx::XvcPtr, ris::SlavePtr>();
#endif
}

