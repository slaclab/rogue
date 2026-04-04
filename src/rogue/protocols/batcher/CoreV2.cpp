/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    AXI Batcher V2 (https://confluence.slac.stanford.edu/x/L2VlK)
 *
 * The batcher protocol starts with a super header followed by a number of
 * frames each with a tail to define the boundaries of each frame.
 *
 * Super Header: 2 bytes
 *
 *    Byte 0:
 *       Bits 3:0 = Version = 2
 *       Bits 7:4 = Reserved
 *    Byte 1:
 *       Bits 15:8 = Sequence # for debug
 *
 * Frame Tail: 7 bytes
 *
 *    Word 0: 4 bytes
 *       bits 31:0 = size
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
#include "rogue/protocols/batcher/CoreV2.h"

#include <inttypes.h>
#include <stdint.h>

#include <cmath>
#include <memory>
#include <thread>

#include "rogue/GeneralError.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/protocols/batcher/Data.h"

namespace rpb = rogue::protocols::batcher;
namespace ris = rogue::interfaces::stream;

//! Class creation
rpb::CoreV2Ptr rpb::CoreV2::create() {
    rpb::CoreV2Ptr p = std::make_shared<rpb::CoreV2>();
    return (p);
}

//! Setup class in python
void rpb::CoreV2::setup_python() {}

//! Creator with version constant
rpb::CoreV2::CoreV2() {
    log_ = rogue::Logging::create("batcher.CoreV2");

    headerSize_ = 2;  // Always 2 byte header
    tailSize_   = 7;  // Always 7 byte tail
    seq_        = 0;
}

//! Deconstructor
rpb::CoreV2::~CoreV2() {}

//! Init size for internal containers
void rpb::CoreV2::initSize(uint32_t size) {
    list_.reserve(size);
    tails_.reserve(size);
}

//! Record count
uint32_t rpb::CoreV2::count() {
    return list_.size();
}

//! Get header size
uint32_t rpb::CoreV2::headerSize() {
    return headerSize_;
}

//! Get beginning of header iterator
ris::FrameIterator rpb::CoreV2::beginHeader() {
    return frame_->begin();
}

//! Get end of header iterator
ris::FrameIterator rpb::CoreV2::endHeader() {
    return frame_->begin() + headerSize_;
}

//! Get tail size
uint32_t rpb::CoreV2::tailSize() {
    return tailSize_;
}

//! Get beginning of tail iterator
ris::FrameIterator rpb::CoreV2::beginTail(uint32_t index) {
    if (index >= tails_.size())
        throw(rogue::GeneralError::create("bather::CoreV2::beginTail",
                                          "Attempt to get tail index %" PRIu32 " in message with %" PRIu32 " tails",
                                          index,
                                          tails_.size()));

    // Invert order on return
    return tails_[(tails_.size() - 1) - index];
}

//! Get end of tail iterator
ris::FrameIterator rpb::CoreV2::endTail(uint32_t index) {
    if (index >= tails_.size())
        throw rogue::GeneralError::create("batcher::CoreV2::tail",
                                          "Attempt to access tail %" PRIu32 " in frame with %" PRIu32 " tails",
                                          index,
                                          tails_.size());

    // Invert order on return
    return tails_[(tails_.size() - 1) - index] + tailSize_;
}

//! Get data
rpb::DataPtr& rpb::CoreV2::record(uint32_t index) {
    if (index >= list_.size())
        throw rogue::GeneralError::create("batcher::CoreV2::record",
                                          "Attempt to access record %" PRIu32 " in frame with %" PRIu32 " records",
                                          index,
                                          tails_.size());

    // Invert order on return
    return list_[(list_.size() - 1) - index];
}

//! Return sequence
uint32_t rpb::CoreV2::sequence() {
    return seq_;
}

//! Process a frame
bool rpb::CoreV2::processFrame(ris::FramePtr frame) {
    uint8_t temp;
    uint32_t rem;
    uint32_t fSize;
    uint8_t dest;
    uint8_t fUser;
    uint8_t lUser;

    // Reset old data
    reset();

    // Store frame reference so header/tail iterators remain valid
    frame_ = frame;

    ris::FrameIterator beg;
    ris::FrameIterator mark;
    ris::FrameIterator tail;

    // Drop errored frames
    if ((frame->getError())) {
        log_->warning("Dropping frame due to error: 0x%" PRIx8, frame->getError());
        return false;
    }

    // Drop small frames: 10 = 2 byte header + 1 byte payload + 7 byte tail
    if ((rem = frame->getPayload()) < 10) {
        log_->warning("Dropping small frame size = %" PRIu32, frame->getPayload());
        return false;
    }

    // Get version & size
    beg = frame->begin();
    ris::fromFrame(beg, 1, &temp);

    /////////////////////////////////////////////////////////////////////////
    // Super-Frame Header in firmware: 2 bytes
    /////////////////////////////////////////////////////////////////////////
    // v.txMaster.tValid               := '1';
    // v.txMaster.tData(3 downto 0)    := x"2";  -- Version = 0x2
    // v.txMaster.tData(7 downto 4)    := Reserved
    // v.txMaster.tData(15 downto 8)   := r.seqCnt;
    // ssiSetUserSof(AXIS_CONFIG_G, v.txMaster, '1');
    /////////////////////////////////////////////////////////////////////////

    // Check version, convert width
    if ((temp & 0xF) != 2) {
        log_->error("Version mismatch. Got %" PRIu8, (temp & 0xF));
        return false;
    }

    // Get sequence #
    ris::fromFrame(beg, 1, &seq_);

    // Compute remaining frame size
    rem -= headerSize_;

    // Set marker to end of frame
    mark = frame->end();

    // Process each frame, stop when we have reached just after the header
    while (mark != beg) {
        // sanity check
        if (rem < tailSize_) {
            log_->error("Not enough space (%" PRIu32 ") for tail (%" PRIu32 ")", rem, tailSize_);
            reset();
            return false;
        }

        // Jump to start of the tail
        mark -= tailSize_;
        rem -= tailSize_;

        // Add tail iterator to end of list
        tails_.push_back(mark);

        // Get tail data, use a new iterator
        tail = mark;
        ris::fromFrame(tail, 4, &fSize);
        ris::fromFrame(tail, 1, &dest);
        ris::fromFrame(tail, 1, &fUser);
        ris::fromFrame(tail, 1, &lUser);

        // Not enough data for rewind value
        if (fSize > rem) {
            log_->error("Not enough space (%" PRIu32 ") for frame (%" PRIu32 ")", rem, fSize);
            reset();
            return false;
        }

        // Set marker to start of data
        mark -= fSize;
        rem -= fSize;

        // Create data record and add it to end of list
        list_.push_back(rpb::Data::create(mark, fSize, dest, fUser, lUser));
    }
    return true;
}

//! Reset data
void rpb::CoreV2::reset() {
    frame_.reset();
    list_.clear();
    tails_.clear();
}
