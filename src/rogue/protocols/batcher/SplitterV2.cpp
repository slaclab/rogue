/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      SLAC Splitter Version 2
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
#include "rogue/Directives.h"

#include "rogue/protocols/batcher/SplitterV2.h"

#include <stdint.h>

#include <cmath>
#include <memory>
#include <thread>

#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/batcher/CoreV2.h"
#include "rogue/protocols/batcher/Data.h"

namespace rpb = rogue::protocols::batcher;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpb::SplitterV2Ptr rpb::SplitterV2::create() {
    rpb::SplitterV2Ptr p = std::make_shared<rpb::SplitterV2>();
    return (p);
}

//! Setup class in python
void rpb::SplitterV2::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rpb::SplitterV2, rpb::SplitterV2Ptr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>(
        "SplitterV2",
        bp::init<>());
#endif
}

//! Creator
rpb::SplitterV2::SplitterV2() : ris::Master(), ris::Slave() {}

//! Deconstructor
rpb::SplitterV2::~SplitterV2() {}

//! Accept a frame from master
void rpb::SplitterV2::acceptFrame(ris::FramePtr frame) {
    rpb::CoreV2 core;
    ris::FramePtr nFrame;
    rpb::DataPtr data;
    uint32_t x;

    // Lock frame
    rogue::GilRelease noGil;
    ris::FrameLockPtr lock = frame->lock();

    core.processFrame(frame);

    for (x = 0; x < core.count(); x++) {
        data = core.record(x);

        // Create a new frame
        nFrame = reqFrame(data->size(), true);
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
