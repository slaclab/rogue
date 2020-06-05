/**
 *-----------------------------------------------------------------------------
 * Title         : SLAC Splitter Version 1
 * ----------------------------------------------------------------------------
 * File          : SplitterV1.h
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
#include <rogue/protocols/batcher/SplitterV1.h>
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
rpb::SplitterV1Ptr rpb::SplitterV1::create() {
   rpb::SplitterV1Ptr p = std::make_shared<rpb::SplitterV1>();
   return(p);
}

//! Setup class in python
void rpb::SplitterV1::setup_python() {
#ifndef NO_PYTHON
   bp::class_<rpb::SplitterV1, rpb::SplitterV1Ptr, bp::bases<ris::Master,ris::Slave>, boost::noncopyable >("SplitterV1",bp::init<>());
#endif
}

//! Creator
rpb::SplitterV1::SplitterV1() : ris::Master(), ris::Slave() { }

//! Deconstructor
rpb::SplitterV1::~SplitterV1() {}

//! Accept a frame from master
void rpb::SplitterV1::acceptFrame ( ris::FramePtr frame ) {
   rpb::CoreV1   core;
   ris::FramePtr nFrame;
   rpb::DataPtr  data;
   uint32_t x;

   // Lock frame
   rogue::GilRelease noGil;
   ris::FrameLockPtr lock = frame->lock();

   core.processFrame(frame);

   for (x=0; x < core.count(); x++) {
      data = core.record(x);

      // Create a new frame
      nFrame = reqFrame(data->size(),true);
      nFrame->setPayload(data->size());

      ris::FrameIterator fIter = nFrame->begin();
      ris::FrameIterator dIter = data->begin();
      ris::copyFrame(dIter, data->size(), fIter);

      // Set flags
      nFrame->setFirstUser(data->fUser());
      nFrame->setLastUser(data->lUser());
      nFrame->setChannel(data->dest());

      sendFrame(nFrame);
   }
}

