/**
 *-----------------------------------------------------------------------------
 * Title      : EPICs PV Attribute Object
 * ----------------------------------------------------------------------------
 * File       : Variable.cpp
 * Created    : 2018-11-18
 * ----------------------------------------------------------------------------
 * Description:
 * Class to store an EPICs PV attributes along with its current value
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

#include <boost/python.hpp>
#include <rogue/protocols/epics/Master.h>
#include <rogue/GeneralError.h>
#include <rogue/ScopedGil.h>
#include <rogue/GilRelease.h>
#include <boost/make_shared.hpp>
#include <boost/make_shared.hpp>

namespace ris = rogue::interfaces::stream;
namespace rpe = rogue::protocols::epics;
namespace bp  = boost::python;

//! Setup class in python
void rpe::Master::setup_python() {

   bp::class_<rpe::Master, rpe::MasterPtr, boost::noncopyable >("Master",bp::init<std::string, uint32_t, std::string>());

   bp::implicitly_convertible<rpe::MasterPtr, ris::MasterPtr>();
   bp::implicitly_convertible<rpe::MasterPtr, rpe::ValuePtr>();
}

//! Class creation
rpe::Master::Master (std::string epicsName, uint32_t max, std::string type) : Value(epicsName) {
   max_ = max;

   // Init gdd record
   this->initGdd(type, false, max_);
}

rpe::Master::~Master() { }

void rpe::Master::valueGet() { }

void rpe::Master::valueSet() {




}

