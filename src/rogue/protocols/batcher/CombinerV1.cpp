/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    AXI Batcher V1 Combiner (SW Batcher)
 *    (https://confluence.slac.stanford.edu/x/th1SDg)
 *
 * Builds a batcher v1 super-frame from individual frames. This is the
 * software inverse of the SplitterV1 unbatcher.
 *
 * Super-frame layout (same as FW batcher):
 *
 *    [Super Header][Record0 Data][Record0 Tail][Record1 Data][Record1 Tail]...
 *
 * Super Header:
 *    Byte 0:
 *       Bits 3:0 = Version = 1
 *       Bits 7:4 = Width = 2 * 2 ^ val Bytes
 *    Byte 1:
 *       Bits 15:8 = Sequence # for debug
 *    Rest of width padded with zeros
 *
 * Frame Tail: Tail size is max(width, 8 bytes). Padded with zeros.
 *    Word 0:
 *       bits 31:0 = size (payload bytes)
 *    Word 1:
 *       bits  7:0  = Destination
 *       bits 15:8  = First user
 *       bits 23:16 = Last user
 *       bits 31:24 = Width (bits 3:0 = width encoding, bits 7:4 = 0)
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
#include "rogue/protocols/batcher/CombinerV1.h"

#include <inttypes.h>
#include <stdint.h>

#include <vector>
#include <string.h>

#include <memory>

#include "rogue/GilRelease.h"
#include "rogue/GeneralError.h"
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
rpb::CombinerV1Ptr rpb::CombinerV1::create(uint8_t width) {
    rpb::CombinerV1Ptr p = std::make_shared<rpb::CombinerV1>(width);
    return (p);
}

//! Setup class in python
void rpb::CombinerV1::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rpb::CombinerV1, rpb::CombinerV1Ptr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>(
        "CombinerV1",
        bp::init<uint8_t>())
        .def("sendBatch", &rpb::CombinerV1::sendBatch)
        .def("getCount", &rpb::CombinerV1::getCount);
#endif
}

//! Creator
rpb::CombinerV1::CombinerV1(uint8_t width) : ris::Master(), ris::Slave() {
    log_ = rogue::Logging::create("batcher.CombinerV1");

    if (width > 5) throw rogue::GeneralError::create("batcher::CombinerV1::CombinerV1", "Invalid width %" PRIu8, width);

    width_ = width;
    seq_   = 0;

    // headerSize = 2 * 2^width
    headerSize_ = 2;
    for (uint8_t i = 0; i < width_; i++) headerSize_ *= 2;

    // tailSize = max(headerSize, 8)
    tailSize_ = (headerSize_ < 8) ? 8 : headerSize_;
}

//! Deconstructor
rpb::CombinerV1::~CombinerV1() {}

//! Accept a frame from master
void rpb::CombinerV1::acceptFrame(ris::FramePtr frame) {
    rogue::GilRelease noGil;
    ris::FrameLockPtr lock = frame->lock();

    std::lock_guard<std::mutex> guard(mtx_);
    queue_.push_back(frame);
}

//! Return queue count
uint32_t rpb::CombinerV1::getCount() {
    std::lock_guard<std::mutex> guard(mtx_);
    return queue_.size();
}

//! Build and send the batched super-frame
void rpb::CombinerV1::sendBatch() {
    std::vector<ris::FramePtr> frames;

    {
        std::lock_guard<std::mutex> guard(mtx_);
        if (queue_.empty()) return;
        frames.swap(queue_);
    }

    // Compute total super-frame size
    uint32_t totalSize = headerSize_;
    for (auto& f : frames) {
        uint32_t payloadSize = f->getPayload();

        // Round payload up to width boundary
        uint32_t padded = payloadSize;
        if ((payloadSize % headerSize_) != 0) padded = ((payloadSize / headerSize_) + 1) * headerSize_;

        totalSize += padded + tailSize_;
    }

    rogue::GilRelease noGil;

    // Allocate the super-frame
    ris::FramePtr sFrame = reqFrame(totalSize, true);
    sFrame->setPayload(totalSize);

    ris::FrameIterator it = sFrame->begin();

    // Write super header
    uint8_t byte0 = (width_ << 4) | 0x1;  // version=1, width encoding
    ris::toFrame(it, 1, &byte0);
    ris::toFrame(it, 1, &seq_);

    // Pad rest of header with zeros
    if (headerSize_ > 2) {
        uint32_t padLen = headerSize_ - 2;
        uint8_t zero = 0;
        for (uint32_t i = 0; i < padLen; i++) ris::toFrame(it, 1, &zero);
    }

    // Write each record: data then tail
    for (auto& f : frames) {
        ris::FrameLockPtr fLock = f->lock();
        uint32_t payloadSize    = f->getPayload();

        // Copy payload data
        ris::FrameIterator srcIt = f->begin();
        ris::copyFrame(srcIt, payloadSize, it);

        // Pad payload to width boundary
        uint32_t padded = payloadSize;
        if ((payloadSize % headerSize_) != 0) padded = ((payloadSize / headerSize_) + 1) * headerSize_;
        uint32_t padLen = padded - payloadSize;
        uint8_t zero    = 0;
        for (uint32_t i = 0; i < padLen; i++) ris::toFrame(it, 1, &zero);

        // Write tail
        // Word 0: size (4 bytes)
        ris::toFrame(it, 4, &payloadSize);

        // Word 1: dest, fUser, lUser, width
        uint8_t dest      = f->getChannel();
        uint8_t fUser     = f->getFirstUser();
        uint8_t lUser     = f->getLastUser();
        uint8_t widthByte = width_;  // FW writes WIDTH_C at tData(59 downto 56)
        ris::toFrame(it, 1, &dest);
        ris::toFrame(it, 1, &fUser);
        ris::toFrame(it, 1, &lUser);
        ris::toFrame(it, 1, &widthByte);

        // Pad rest of tail with zeros (tailSize_ - 8 bytes already written)
        if (tailSize_ > 8) {
            uint32_t tailPad = tailSize_ - 8;
            for (uint32_t i = 0; i < tailPad; i++) ris::toFrame(it, 1, &zero);
        }
    }

    seq_++;

    sendFrame(sFrame);
}
