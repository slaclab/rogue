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
#include <boost/thread.hpp>
#include <boost/make_shared.hpp>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/protocols/srp/Cmd.h>

namespace bp = boost::python;
namespace rps = rogue::protocols::srp;
namespace ris = rogue::interfaces::stream;

//! Class creation
rps::CmdPtr rps::Cmd::create () {
   rps::CmdPtr p = boost::make_shared<rps::Cmd>();
   return(p);
}

//! Setup class in python
void rps::Cmd::setup_python() {

   bp::class_<rps::Cmd, rps::CmdPtr, bp::bases<ris::Master>, boost::noncopyable >("Cmd",bp::init<>())
       .def("sendCmd", &rps::Cmd::sendCmd)
      .def("create",         &rps::Cmd::create)
      .staticmethod("create")
   ;

}

//! Creator with version constant
rps::Cmd::Cmd() : ris::Master() { }

//! Deconstructor
rps::Cmd::~Cmd() {}

//! Post a transaction
void rps::Cmd::sendCmd(uint8_t opCode, uint32_t context) {
   ris::FramePtr  frame;
   uint32_t  frameSize;
   uint32_t  temp;
   uint32_t  cnt;

   // Always 4x 32-bit words
   frameSize = 16;

   // Request frame
   frame = reqFrame(frameSize, true, 0);

   // First 32-bit value is context
   temp = context;
   cnt  = frame->write(&(temp), 0, 4);
   
   // Second 32-bit value is opcode
   temp = opCode;
   cnt  += frame->write(&(temp), cnt, 4);

   // Last two fields are zero
   temp = 0;
   cnt += frame->write(&temp, cnt, 4);
   cnt += frame->write(&temp, cnt, 4);   

   sendFrame(frame);
}



