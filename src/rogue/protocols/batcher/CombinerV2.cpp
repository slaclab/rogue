/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    AXI Batcher V2 Combiner (SW Batcher)
 *    (https://confluence.slac.stanford.edu/x/L2VlK)
 *
 * Builds a batcher v2 super-frame from individual frames. This is the
 * software inverse of the SplitterV2 unbatcher.
 *
 * Super-frame layout (same as FW batcher):
 *
 *    [Super Header (2 bytes)][Record0 Data][Record0 Tail (7 bytes)]...
 *
 * Super Header: 2 bytes
 *    Byte 0:
 *       Bits 3:0 = Version = 2
 *       Bits 7:4 = Reserved
 *    Byte 1:
 *       Bits 15:8 = Sequence # for debug
 *
 * Frame Tail: 7 bytes
 *    Word 0: 4 bytes
 *       bits 31:0 = size (payload bytes)
 *    Word 1: 3 bytes
 *       bits  7:0  = Destination
 *       bits 15:8  = First user
 *       bits 23:16 = Last user
 *
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
#include "rogue/protocols/batcher/CombinerV2.h"

#include <inttypes.h>
#include <stdint.h>

#include <vector>
#include <string.h>

#include <memory>

#include "rogue/GilRelease.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rpb = rogue::protocols::batcher;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rpb::CombinerV2Ptr rpb::CombinerV2::create() {
    rpb::CombinerV2Ptr p = std::make_shared<rpb::CombinerV2>();
    return (p);
}

//! Setup class in python
void rpb::CombinerV2::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rpb::CombinerV2, rpb::CombinerV2Ptr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>(
        "CombinerV2",
        bp::init<>())
        .def("sendBatch", &rpb::CombinerV2::sendBatch)
        .def("getCount", &rpb::CombinerV2::getCount);
#endif
}

//! Creator
rpb::CombinerV2::CombinerV2() : ris::Master(), ris::Slave() {
    log_ = rogue::Logging::create("batcher.CombinerV2");
    seq_ = 0;
}

//! Deconstructor
rpb::CombinerV2::~CombinerV2() {}

//! Accept a frame from master
void rpb::CombinerV2::acceptFrame(ris::FramePtr frame) {
    rogue::GilRelease noGil;
    ris::FrameLockPtr lock = frame->lock();

    std::lock_guard<std::mutex> guard(mtx_);
    queue_.push_back(frame);
}

//! Return queue count
uint32_t rpb::CombinerV2::getCount() {
    std::lock_guard<std::mutex> guard(mtx_);
    return queue_.size();
}

//! Build and send the batched super-frame
void rpb::CombinerV2::sendBatch() {
    const uint32_t headerSize = 2;
    const uint32_t tailSize   = 7;

    std::vector<ris::FramePtr> frames;

    {
        std::lock_guard<std::mutex> guard(mtx_);
        if (queue_.empty()) return;
        frames.swap(queue_);
    }

    // Compute total super-frame size
    uint32_t totalSize = headerSize;
    for (auto& f : frames) {
        totalSize += f->getPayload() + tailSize;
    }

    rogue::GilRelease noGil;

    // Allocate the super-frame
    ris::FramePtr sFrame = reqFrame(totalSize, true);
    sFrame->setPayload(totalSize);

    ris::FrameIterator it = sFrame->begin();

    // Write super header (2 bytes)
    uint8_t byte0 = 0x02;  // version=2, reserved bits=0
    ris::toFrame(it, 1, &byte0);
    ris::toFrame(it, 1, &seq_);

    // Write each record: data then tail
    for (auto& f : frames) {
        ris::FrameLockPtr fLock = f->lock();
        uint32_t payloadSize    = f->getPayload();

        // Copy payload data
        ris::FrameIterator srcIt = f->begin();
        ris::copyFrame(srcIt, payloadSize, it);

        // Write tail (7 bytes)
        // Word 0: size (4 bytes)
        ris::toFrame(it, 4, &payloadSize);

        // Word 1: dest, fUser, lUser (3 bytes)
        uint8_t dest  = f->getChannel();
        uint8_t fUser = f->getFirstUser();
        uint8_t lUser = f->getLastUser();
        ris::toFrame(it, 1, &dest);
        ris::toFrame(it, 1, &fUser);
        ris::toFrame(it, 1, &lUser);
    }

    seq_++;

    sendFrame(sFrame);
}
