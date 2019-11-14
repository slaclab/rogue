/**
 *-----------------------------------------------------------------------------
 * Title      : Stream interface pipe (master & slave)
 * ----------------------------------------------------------------------------
 * File          : Pipe.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 11/13/2019
 *-----------------------------------------------------------------------------
 * Description :
 *    Stream master / slave combination 
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to 
 * the license terms in the LICENSE.txt file found in the top-level directory 
 * of this distribution and at: 
    * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
 * No part of the rogue software platform, including this file, may be 
 * copied, modified, propagated, or distributed except according to the terms 
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
**/
#include <stdint.h>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Pipe.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::PipePtr ris::Pipe::create () {
   ris::PipePtr p = std::make_shared<ris::Pipe>();
   return(p);
}

//! Setup class in python
void ris::Pipe::setup_python() {
#ifndef NO_PYTHON

   bp::class_<ris::Pipe, ris::PipePtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Pipe",bp::init<>())
      .def("__equals__", &ris::Pipe::connect);

   bp::implicitly_convertible<ris::PipePtr, ris::MasterPtr>();
   bp::implicitly_convertible<ris::PipePtr, ris::SlavePtr>();

#endif
}

//! Creator
ris::Pipe::Pipe() : ris::Master(), ris::Slave() { }

//! Deconstructor
ris::Pipe::~Pipe() {}

//! Bi-Directional Connect
void ris::Pipe::connect(ris::PipePtr other) {
   this->addSlave(other);
   other->addSlave(shared_from_this<ris::Pipe>());
}

