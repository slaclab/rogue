/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * RSSI Controller
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
#include "rogue/protocols/rssi/Controller.h"

#include <inttypes.h>
#include <sys/time.h>
#include <unistd.h>

#include <cmath>
#include <cstdlib>
#include <cstring>
#include <map>
#include <memory>
#include <utility>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Helpers.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Header.h"
#include "rogue/protocols/rssi/Transport.h"

namespace rpr = rogue::protocols::rssi;
namespace ris = rogue::interfaces::stream;

//! Class creation
rpr::ControllerPtr rpr::Controller::create(uint32_t segSize,
                                           rpr::TransportPtr tran,
                                           rpr::ApplicationPtr app,
                                           bool server) {
    rpr::ControllerPtr r = std::make_shared<rpr::Controller>(segSize, tran, app, server);
    return (r);
}

//! Creator
rpr::Controller::Controller(uint32_t segSize, rpr::TransportPtr tran, rpr::ApplicationPtr app, bool server) {
    app_    = app;
    tran_   = tran;
    server_ = server;

    locTryPeriod_ = 100;

    // Busy after two entries
    appQueue_.setThold(2);

    dropCount_ = 0;
    nextSeqRx_ = 0;
    lastAckRx_ = 0;
    locBusy_   = false;
    remBusy_   = false;

    lastSeqRx_ = 0;
    ackSeqRx_  = 0;

    state_ = StClosed;
    gettimeofday(&stTime_, NULL);
    downCount_   = 0;
    retranCount_ = 0;

    txListCount_ = 0;
    lastAckTx_   = 0;
    locSequence_ = 100;
    gettimeofday(&txTime_, NULL);

    locMaxBuffers_ = 32;  // MAX_NUM_OUTS_SEG_G in FW
    locMaxSegment_ = segSize;
    locCumAckTout_ = 5;     // ACK_TOUT_G in FW, 5mS
    locRetranTout_ = 20;    // RETRANS_TOUT_G in FW, 2hmS
    locNullTout_   = 1000;  // NULL_TOUT_G in FW, 1S
    locMaxRetran_  = 15;    // MAX_RETRANS_CNT_G in FW
    locMaxCumAck_  = 2;     // MAX_CUM_ACK_CNT_G in FW

    curMaxBuffers_ = 32;  // MAX_NUM_OUTS_SEG_G in FW
    curMaxSegment_ = segSize;
    curCumAckTout_ = 5;     // ACK_TOUT_G in FW, 5mS
    curRetranTout_ = 20;    // RETRANS_TOUT_G in FW, 2hmS
    curNullTout_   = 1000;  // NULL_TOUT_G in FW, 1S
    curMaxRetran_  = 15;    // MAX_RETRANS_CNT_G in FW
    curMaxCumAck_  = 2;     // MAX_CUM_ACK_CNT_G in FW

    locConnId_ = 0x12345678;
    remConnId_ = 0;

    convTime(tryPeriodD1_, locTryPeriod_);
    convTime(tryPeriodD4_, locTryPeriod_ / 4);
    convTime(retranToutD1_, curRetranTout_);
    convTime(nullToutD3_, curNullTout_ / 3);
    convTime(cumAckToutD1_, curCumAckTout_);
    convTime(cumAckToutD2_, curCumAckTout_ / 2);

    memset(&zeroTme_, 0, sizeof(struct timeval));

    rogue::defaultTimeout(timeout_);

    locBusyCnt_ = 0;
    remBusyCnt_ = 0;

    log_ = rogue::Logging::create("rssi.controller");

    thread_ = NULL;
}

//! Destructor
rpr::Controller::~Controller() {
    stop();
}

//! Stop queues
void rpr::Controller::stopQueue() {
    appQueue_.stop();
}

//! Close
void rpr::Controller::stop() {
    if (thread_) {
        rogue::GilRelease noGil;
        threadEn_ = false;
        thread_->join();
        thread_.reset();
        state_ = StClosed;
    }
}

//! Start
void rpr::Controller::start() {
    if (!thread_) {
        state_    = StClosed;
        threadEn_ = true;
        thread_ = std::make_unique<std::thread>(&rpr::Controller::runThread, this);

        // Set a thread name
#ifndef __MACH__
        pthread_setname_np(thread_->native_handle(), "RssiControler");
#endif
    }
}

//! Transport frame allocation request
ris::FramePtr rpr::Controller::reqFrame(uint32_t size) {
    ris::FramePtr frame;
    ris::BufferPtr buffer;
    uint32_t nSize;

    // Request only single buffer frames.
    // Frame size returned is never greater than remote max size
    // or local segment size
    nSize = size + rpr::Header::HeaderSize;
    if (nSize > curMaxSegment_ && curMaxSegment_ > 0) nSize = curMaxSegment_;
    if (nSize > locMaxSegment_) nSize = locMaxSegment_;

    // Forward frame request to transport slave
    frame  = tran_->reqFrame(nSize, false);
    buffer = *(frame->beginBuffer());

    // Make sure there is enough room the buffer for our header
    if (buffer->getAvailable() < rpr::Header::HeaderSize)
        throw(rogue::GeneralError::create("rssi::Controller::reqFrame",
                                          "Buffer size %" PRId32 " is less than min header size %" PRIu32,
                                          rpr::Header::HeaderSize,
                                          buffer->getAvailable()));

    // Update buffer to include our header space.
    buffer->adjustHeader(rpr::Header::HeaderSize);

    // Recreate frame to ensure outbound only has a single buffer
    frame = ris::Frame::create();
    frame->appendBuffer(buffer);

    // Return frame
    return (frame);
}

//! Frame received at transport interface
void rpr::Controller::transportRx(ris::FramePtr frame) {
    std::map<uint8_t, rpr::HeaderPtr>::iterator it;

    rpr::HeaderPtr head = rpr::Header::create(frame);

    rogue::GilRelease noGil;
    ris::FrameLockPtr flock = frame->lock();

    if (frame->getError() || frame->isEmpty() || !head->verify()) {
        log_->warning("Dumping bad frame state=%" PRIu32 " server=%d", state_, server_);
        dropCount_++;
        return;
    }

    log_->debug("RX frame: state=%" PRIu32 " server=%d size=%" PRIu32 " syn=%d ack=%d"
                " nul=%d, bsy=%d, rst=%d, ack#=%" PRIu8 " seq=%" PRIu8 ", nxt=%" PRIu8,
                state_,
                server_,
                frame->getPayload(),
                head->syn,
                head->ack,
                head->nul,
                head->busy,
                head->rst,
                head->acknowledge,
                head->sequence,
                nextSeqRx_);

    // Ack set
    if (head->ack && (head->acknowledge != lastAckRx_)) {
        std::unique_lock<std::mutex> lock(txMtx_);

        do {
            txList_[++lastAckRx_].reset();
            if (txListCount_ != 0) txListCount_--;
        } while (lastAckRx_ != head->acknowledge);
    }

    // Check for busy state transition
    if (!remBusy_ && head->busy) remBusyCnt_++;

    // Update busy bit
    remBusy_ = head->busy;

    // Reset
    if (head->rst) {
        if (state_ == StOpen || state_ == StWaitSyn) {
            stQueue_.push(head);
        }

        // Syn frame goes to state machine if state = open
        // or we are waiting for ack replay
    } else if (head->syn) {
        if (state_ == StOpen || state_ == StWaitSyn) {
            lastSeqRx_ = head->sequence;
            nextSeqRx_ = lastSeqRx_ + 1;
            stQueue_.push(head);
        }

        // Data or NULL in the correct sequence go to application
    } else if (state_ == StOpen && (head->nul || frame->getPayload() > rpr::Header::HeaderSize)) {
        if (head->sequence == nextSeqRx_) {
            // log_->warning("Data or NULL in the correct sequence go to application: nextSeqRx_=0x%" PRIx8,
            // nextSeqRx_);

            lastSeqRx_ = nextSeqRx_;
            nextSeqRx_ = nextSeqRx_ + 1;
            appQueue_.push(head);

            // There are elements in ooo (out-of-order) queue
            if (!oooQueue_.empty()) {
                // First remove received sequence number from queue to avoid duplicates
                if ((it = oooQueue_.find(head->sequence)) != oooQueue_.end()) {
                    log_->warning("Removed duplicate frame. server=%d, head->sequence=%" PRIu8
                                  ", next sequence=%" PRIu8,
                                  server_,
                                  head->sequence,
                                  nextSeqRx_);
                    dropCount_++;
                    oooQueue_.erase(it);
                }

                // Get next entries from ooo (out-of-order) queue if they exist
                // This works because max outstanding will never be the full range of ids
                // otherwise this could be stale data from previous ids
                while ((it = oooQueue_.find(nextSeqRx_)) != oooQueue_.end()) {
                    lastSeqRx_ = nextSeqRx_;
                    nextSeqRx_ = nextSeqRx_ + 1;

                    appQueue_.push(it->second);
                    log_->info("Using frame from ooo queue. server=%d, head->sequence=%" PRIu8,
                               server_,
                               (it->second)->sequence);
                    oooQueue_.erase(it);
                }
            }

            // Notify after the last sequence update
            stCond_.notify_all();

            // Check if received frame is already in out of order queue
        } else if ((it = oooQueue_.find(head->sequence)) != oooQueue_.end()) {
            log_->warning("Dropped duplicate frame. server=%d, head->sequence=%" PRIu8
                          ", next sequence=%" PRIu8,
                          server_,
                          head->sequence,
                          nextSeqRx_);
            dropCount_++;

            // Add to out of order queue in case things arrive out of order
            // Make sure received sequence is in window. There may be a better way
            // to do this while handling the 8 bit rollover
        } else {
            uint8_t x         = nextSeqRx_;
            uint8_t windowEnd = (nextSeqRx_ + curMaxBuffers_ + 1);

            while (++x != windowEnd) {
                if (head->sequence == x) {
                    oooQueue_.insert(std::make_pair(head->sequence, head));
                    log_->info("Adding frame to ooo queue. server=%d, head->sequence=%" PRIu8
                               ", nextSeqRx_=%" PRIu8 ", windowsEnd=%" PRIu8,
                               server_,
                               head->sequence,
                               nextSeqRx_,
                               windowEnd);
                    break;
                }
            }

            if (x == windowEnd) {
                log_->warning("Dropping out of window frame. server=%d, head->sequence=%" PRIu8
                              ", nextSeqRx_=%" PRIu8 ", windowsEnd=%" PRIu8,
                              server_,
                              head->sequence,
                              nextSeqRx_,
                              windowEnd);
                dropCount_++;
            }
        }
    }
}

//! Frame transmit at application interface
// Called by application class thread
ris::FramePtr rpr::Controller::applicationTx() {
    ris::FramePtr frame;
    rpr::HeaderPtr head;

    rogue::GilRelease noGil;

    do {
        if ((head = appQueue_.pop()) == NULL) return (frame);
        stCond_.notify_all();

        frame                   = head->getFrame();
        ris::FrameLockPtr flock = frame->lock();

        ackSeqRx_ = head->sequence;

        // Drop NULL frames
        if (head->nul) {
            head.reset();
            frame.reset();
        } else {
            (*(frame->beginBuffer()))->adjustHeader(rpr::Header::HeaderSize);
        }
    } while (!frame);

    return (frame);
}

//! Frame received at application interface
void rpr::Controller::applicationRx(ris::FramePtr frame) {
    ris::FramePtr tranFrame;
    struct timeval startTime;

    gettimeofday(&startTime, NULL);

    rogue::GilRelease noGil;
    ris::FrameLockPtr flock = frame->lock();

    if (frame->isEmpty()) {
        log_->warning("Dropping empty application frame");
        return;
    }

    if (frame->getError()) {
        log_->warning("Dropping errored application frame");
        return;
    }

    // Adjust header in first buffer
    (*(frame->beginBuffer()))->adjustHeader(-rpr::Header::HeaderSize);

    // Map to RSSI
    rpr::HeaderPtr head = rpr::Header::create(frame);
    head->ack           = true;
    flock->unlock();

    // Connection is closed
    if (state_ != StOpen) {
        return;
    }

    // Wait while busy either by flow control or buffer starvation.
    {
        std::unique_lock<std::mutex> lk(stMtx_);
        while (txListCount_ >= curMaxBuffers_) {
            stCond_.wait_for(lk, std::chrono::microseconds(10),
                             [this] { return txListCount_ < curMaxBuffers_; });
            if (timePassed(startTime, timeout_)) {
                gettimeofday(&startTime, NULL);
                log_->critical("Controller::applicationRx: Timeout waiting for outbound queue after %" PRIu32
                               ".%" PRIu32 " seconds! May be caused by outbound backpressure.",
                               timeout_.tv_sec,
                               timeout_.tv_usec);
            }
        }
    }

    // Transmit
    transportTx(head, true, false);
    stCond_.notify_all();
}

//! Get state
bool rpr::Controller::getOpen() {
    return (state_ == StOpen);
}

//! Get Down Count
uint32_t rpr::Controller::getDownCount() {
    return (downCount_);
}

//! Get Drop Count
uint32_t rpr::Controller::getDropCount() {
    return (dropCount_);
}

//! Get Retransmit Count
uint32_t rpr::Controller::getRetranCount() {
    return (retranCount_);
}

//! Get locBusy
bool rpr::Controller::getLocBusy() {
    bool queueBusy = appQueue_.busy();
    if (!locBusy_ && queueBusy) locBusyCnt_++;
    locBusy_ = queueBusy;
    return (locBusy_);
}

//! Get locBusyCnt
uint32_t rpr::Controller::getLocBusyCnt() {
    return (locBusyCnt_);
}

//! Get remBusy
bool rpr::Controller::getRemBusy() {
    return (remBusy_);
}

//! Get remBusyCnt
uint32_t rpr::Controller::getRemBusyCnt() {
    return (remBusyCnt_);
}

void rpr::Controller::setLocTryPeriod(uint32_t val) {
    if (val == 0)
        throw rogue::GeneralError::create("Rssi::Controller::setLocTryPeriod",
                                          "Invalid LocTryPeriod Value = %" PRIu32,
                                          val);
    locTryPeriod_ = val;
    convTime(tryPeriodD1_, locTryPeriod_);
    convTime(tryPeriodD4_, locTryPeriod_ / 4);
}

uint32_t rpr::Controller::getLocTryPeriod() {
    return locTryPeriod_;
}

void rpr::Controller::setLocMaxBuffers(uint8_t val) {
    if (val == 0)
        throw rogue::GeneralError::create("Rssi::Controller::setLocMaxBuffers",
                                          "Invalid LocMaxBuffers Value = %" PRIu8,
                                          val);

    locMaxBuffers_ = val;
}

uint8_t rpr::Controller::getLocMaxBuffers() {
    return locMaxBuffers_;
}

void rpr::Controller::setLocMaxSegment(uint16_t val) {
    if (val == 0)
        throw rogue::GeneralError::create("Rssi::Controller::setLocMaxSegment",
                                          "Invalid LocMaxSegment Value = %" PRIu16,
                                          val);
    locMaxSegment_ = val;
}

uint16_t rpr::Controller::getLocMaxSegment() {
    return locMaxSegment_;
}

void rpr::Controller::setLocCumAckTout(uint16_t val) {
    if (val == 0)
        throw rogue::GeneralError::create("Rssi::Controller::setLocCumAckTout",
                                          "Invalid LocCumAckTout Value = %" PRIu16,
                                          val);
    locCumAckTout_ = val;
}

uint16_t rpr::Controller::getLocCumAckTout() {
    return locCumAckTout_;
}

void rpr::Controller::setLocRetranTout(uint16_t val) {
    if (val == 0)
        throw rogue::GeneralError::create("Rssi::Controller::setLocRetranTout",
                                          "Invalid LocRetranTout Value = %" PRIu16,
                                          val);
    locRetranTout_ = val;
}

uint16_t rpr::Controller::getLocRetranTout() {
    return locRetranTout_;
}

void rpr::Controller::setLocNullTout(uint16_t val) {
    if (val == 0)
        throw rogue::GeneralError::create("Rssi::Controller::setLocNullTout",
                                          "Invalid LocNullTout Value = %" PRIu16,
                                          val);
    locNullTout_ = val;
}

uint16_t rpr::Controller::getLocNullTout() {
    return locNullTout_;
}

void rpr::Controller::setLocMaxRetran(uint8_t val) {
    if (val == 0)
        throw rogue::GeneralError::create("Rssi::Controller::setLocMaxRetran",
                                          "Invalid LocMaxRetran Value = %" PRIu8,
                                          val);
    locMaxRetran_ = val;
}

uint8_t rpr::Controller::getLocMaxRetran() {
    return locMaxRetran_;
}

void rpr::Controller::setLocMaxCumAck(uint8_t val) {
    if (val == 0)
        throw rogue::GeneralError::create("Rssi::Controller::setLocMaxAck", "Invalid LocMaxAck Value = %" PRIu8, val);
    locMaxCumAck_ = val;
}

uint8_t rpr::Controller::getLocMaxCumAck() {
    return locMaxCumAck_;
}

uint8_t rpr::Controller::curMaxBuffers() {
    return curMaxBuffers_;
}

uint16_t rpr::Controller::curMaxSegment() {
    return curMaxSegment_;
}

uint16_t rpr::Controller::curCumAckTout() {
    return curCumAckTout_;
}

uint16_t rpr::Controller::curRetranTout() {
    return curRetranTout_;
}

uint16_t rpr::Controller::curNullTout() {
    return curNullTout_;
}

#include "ControllerImpl.hpp"  // NOLINT(build/include_subdir)
