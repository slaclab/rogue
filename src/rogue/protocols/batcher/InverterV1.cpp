/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Inverter Version 1
 * ----------------------------------------------------------------------------
 * File          : InverterV1.h
 * Author        : Ryan Herbst <rherbst@slac.stanford.edu>
 * Created       : 10/26/2018
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
#include <rogue/interfaces/stream/Slave.h>
#include <rogue/interfaces/stream/Frame.h>
#include <rogue/interfaces/stream/FrameLock.h>
#include <rogue/interfaces/stream/FrameIterator.h>
#include <rogue/protocols/batcher/InverterV1.h>
#include <rogue/protocols/batcher/CoreV1.h>
#include <rogue/protocols/batcher/Data.h>
#include <rogue/Logging.h>
#include <rogue/GilRelease.h>
#include <math.h>

namespace rpb = rogue::protocols::batcher;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
namespace bp  = boost::python;
#endif

//! Class creation
rpb::InverterV1Ptr rpb::InverterV1::create() {
   rpb::InverterV1Ptr p = std::make_shared<rpb::InverterV1>();
   return(p);
}

//! Setup class in python
void rpb::InverterV1::setup_python() {
#ifndef NO_PYTHON
   bp::class_<rpb::InverterV1, rpb::InverterV1Ptr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("InverterV1",bp::init<>());
#endif
}

//! Creator
rpb::InverterV1::InverterV1() : ris::Master(), ris::Slave() { }

//! Deconstructor
rpb::InverterV1::~InverterV1() {}

//! Accept a frame from master
void rpb::InverterV1::acceptFrame ( ris::FramePtr frame ) {
   rpb::CoreV1   core;
   rpb::DataPtr  data;
   uint32_t x;

   // Lock frame
   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();

   core.processFrame(frame);

   // Header and tail size must match, must have at least one record
   if ( (core.headerSize() != core.tailSize()) || (core.count() == 0) ) return;

   // Copy first tail to head
   std::memcpy(core.beginHeader().ptr(), core.beginTail(0).ptr(), core.headerSize());

   // Copy remaining tails
   for (x=1; x < core.count(); x++)
      std::memcpy(core.beginTail(x-1).ptr(), core.beginTail(x).ptr(), core.headerSize());

   // Remove last tail from frame
   frame->adjustPayload(-1 * core.headerSize());

   // Send the frame
   lock->unlock();
   sendFrame(frame);
}

