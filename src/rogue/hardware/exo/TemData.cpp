/**
 *-----------------------------------------------------------------------------
 * Title      : EXO TEM Base Class
 * ----------------------------------------------------------------------------
 * File       : TemData.cpp
 * Author     : Ryan Herbst, rherbst@slac.stanford.edu
 * Created    : 2017-09-17
 * Last update: 2017-09-17
 * ----------------------------------------------------------------------------
 * Description:
 * Class for interfacing to Tem Driver.
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
#include <rogue/hardware/exo/TemData.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Buffer.h>
#include <boost/make_shared.hpp>

namespace rhe = rogue::hardware::exo;
namespace ris = rogue::interfaces::stream;
namespace bp  = boost::python;

//! Class creation
rhe::TemDataPtr rhe::TemData::create () {
   rhe::TemDataPtr r = boost::make_shared<rhe::TemData>();
   return(r);
}

//! Creator
rhe::TemData::TemData() : Tem("/dev/temcard_0",false) { }

//! Destructor
rhe::TemData::~TemData() { }

void rhe::TemData::setup_python () {

   bp::class_<rhe::TemData, rhe::TemDataPtr, bp::bases<rhe::Tem>, boost::noncopyable >("TemData",bp::init<>())
      .def("create",         &rhe::TemData::create)
      .staticmethod("create")
   ;

   bp::implicitly_convertible<rhe::TemDataPtr, rhe::TemPtr>();

}

