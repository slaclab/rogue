/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) SrpV0
 * ----------------------------------------------------------------------------
 * File          : SrpV0.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 09/17/2016
 * Last update   : 09/17/2016
 *-----------------------------------------------------------------------------
 * Description :
 *    CMD protocol bridge, Version 0
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
#include <thread>
#include <memory>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/protocols/srp/Cmd.h>

namespace rps = rogue::protocols::srp;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rps::CmdPtr rps::Cmd::create () {
   rps::CmdPtr p = std::make_shared<rps::Cmd>();
   return(p);
}

//! Setup class in python
void rps::Cmd::setup_python() {
#ifndef NO_PYTHON

   bp::class_<rps::Cmd, rps::CmdPtr, bp::bases<ris::Master>, boost::noncopyable >("Cmd",bp::init<>())
       .def("sendCmd", &rps::Cmd::sendCmd)
   ;
#endif
}

//! Creator with version constant
rps::Cmd::Cmd() : ris::Master() { }

//! Deconstructor
rps::Cmd::~Cmd() {}

//! Post a transaction
void rps::Cmd::sendCmd(uint8_t opCode, uint32_t context) {
   ris::FrameIterator it;
   ris::FramePtr frame;
   uint32_t txData[4];

   // Build frame
   txData[0] = context;
   txData[1] = opCode;
   txData[2] = 0;
   txData[3] = 0;

   // Request frame
   frame = reqFrame(sizeof(txData), true);
   frame->setPayload(sizeof(txData));
   it = frame->begin();

   // Copy frame
   ris::toFrame(it,sizeof(txData),txData);
   sendFrame(frame);
}

