/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Register Protocol (SRP) Filter
 * ----------------------------------------------------------------------------
 * File          : Filter.cpp
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 11/01/2018
 *-----------------------------------------------------------------------------
 * Description :
 *    AXI Stream Filter
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
#include <memory>
#include <rogue/interfaces/stream/Master.h>
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/Filter.h>
#include <rogue/Logging.h>

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
ris::FilterPtr ris::Filter::create(bool dropErrors, uint8_t channel) {
   ris::FilterPtr p = std::make_shared<ris::Filter>(dropErrors,channel);
   return(p);
}

//! Setup class in python
void ris::Filter::setup_python() {
#ifndef NO_PYTHON
   bp::class_<ris::Filter, ris::FilterPtr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("Filter",bp::init<bool,uint8_t>());
#endif
}

//! Creator with version constant
ris::Filter::Filter(bool dropErrors, uint8_t channel) : ris::Master(), ris::Slave() {
   dropErrors_ = dropErrors;
   channel_ = channel;

   log_ = rogue::Logging::create("stream.Filter");
}

//! Deconstructor
ris::Filter::~Filter() {}

//! Accept a frame from master
void ris::Filter::acceptFrame ( ris::FramePtr frame ) {

   // Drop channel mismatches
   if ( frame->getChannel() != channel_ ) return;

   // Drop errored frames
   if ( dropErrors_ && (frame->getError() != 0) ) {
      log_->debug("Dropping errored frame: Channel=%i, Error=0x%x",channel_, frame->getError());
      return;
   }

   sendFrame(frame);
}

