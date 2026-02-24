/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *      SLAC Inverter Version 2
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

#include "rogue/protocols/batcher/InverterV2.h"

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
rpb::InverterV2Ptr rpb::InverterV2::create() {
    rpb::InverterV2Ptr p = std::make_shared<rpb::InverterV2>();
    return (p);
}

//! Setup class in python
void rpb::InverterV2::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rpb::InverterV2, rpb::InverterV2Ptr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>(
        "InverterV2",
        bp::init<>());
#endif
}

//! Creator
rpb::InverterV2::InverterV2() : ris::Master(), ris::Slave() {}

//! Deconstructor
rpb::InverterV2::~InverterV2() {}

//! Accept a frame from master
void rpb::InverterV2::acceptFrame(ris::FramePtr frame) {
    rpb::CoreV2 core;
    rpb::DataPtr data;
    uint32_t x;

    // Lock frame
    rogue::GilRelease noGil;
    ris::FrameLockPtr lock = frame->lock();

    core.processFrame(frame);

    // Must have at least one record
    if (core.count() == 0) return;

    // Copy first tail to head
    std::memcpy(core.beginHeader().ptr(), core.beginTail(0).ptr(), core.headerSize());

    // Copy remaining tails
    for (x = 1; x < core.count(); x++)
        std::memcpy(core.beginTail(x - 1).ptr(), core.beginTail(x).ptr(), core.headerSize());

    // Remove last tail from frame
    frame->adjustPayload(-1 * core.headerSize());

    // Send the frame
    lock->unlock();
    sendFrame(frame);
}
