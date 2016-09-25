/**
 *-----------------------------------------------------------------------------
 * Title      : EXO TEM Base Class
 * ----------------------------------------------------------------------------
 * File       : TemCmd.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to Tem Driver.
 * TODO
 *    Add lock in accept to make sure we can handle situation where close 
 *    occurs while a frameAccept or frameRequest
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
#include <rogue/hardware/exo/TemCmd.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <boost/make_shared.hpp>

namespace rhe = rogue::hardware::exo;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rhe::TemCmdPtr rhe::TemCmd::create () {
   rhe::TemCmdPtr r = boost::make_shared<rhe::TemCmd>();
   return(r);
}

//! Creator
rhe::TemCmd::TemCmd() : Tem("/dev/temcard_0",false) { }

//! Destructor
rhe::TemCmd::~TemCmd() { }

void rhe::TemCmd::setup_python () {

   bp::class_<rhe::TemCmd, bp::bases<rhe::Tem>, rhe::TemCmdPtr, boost::noncopyable >("TemCmd",bp::init<>())
      .def("create",         &rhe::TemCmd::create)
      .staticmethod("create")
   ;
}

