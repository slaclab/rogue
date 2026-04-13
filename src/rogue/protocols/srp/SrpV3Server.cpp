/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SRP protocol server, Version 3
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
#include "rogue/Directives.h"

#include "rogue/protocols/srp/SrpV3Server.h"

#include <inttypes.h>
#include <stdint.h>

#include <cstring>
#include <memory>
#include <random>
#include <utility>
#include <vector>

#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rps = rogue::protocols::srp;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rps::SrpV3ServerPtr rps::SrpV3Server::create() {
    rps::SrpV3ServerPtr p = std::make_shared<rps::SrpV3Server>();
    return (p);
}

//! Setup class in python
void rps::SrpV3Server::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rps::SrpV3Server, rps::SrpV3ServerPtr, bp::bases<ris::Master, ris::Slave>, boost::noncopyable>(
        "SrpV3Server",
        bp::init<>());
    bp::implicitly_convertible<rps::SrpV3ServerPtr, ris::MasterPtr>();
    bp::implicitly_convertible<rps::SrpV3ServerPtr, ris::SlavePtr>();
#endif
}

//! Constructor
rps::SrpV3Server::SrpV3Server() : ris::Master(), ris::Slave() {
    log_      = rogue::Logging::create("SrpV3Server");
    totAlloc_ = 0;
    threadEn_ = true;
    thread_   = std::thread(&SrpV3Server::runThread, this);
}

//! Destructor
rps::SrpV3Server::~SrpV3Server() {
    stop();

    MemoryMap::iterator it = memMap_.begin();
    while (it != memMap_.end()) {
        free(it->second);
        ++it;
    }
}

//! Stop the worker thread
void rps::SrpV3Server::stop() {
    {
        std::lock_guard<std::mutex> lock(queMtx_);
        threadEn_ = false;
    }
    queCond_.notify_all();

    if (thread_.joinable()) thread_.join();

    ris::Master::stop();
}

//! Worker thread
void rps::SrpV3Server::runThread() {
    ris::FramePtr frame;
    log_->debug("Worker thread started");

    while (threadEn_) {
        {
            std::unique_lock<std::mutex> lock(queMtx_);
            queCond_.wait(lock, [this] { return !queue_.empty() || !threadEn_; });

            if (!threadEn_) break;

            frame = queue_.front();
            queue_.pop();
        }

        processFrame(frame);
    }

    log_->debug("Worker thread stopped");
}

//! Allocate a new 4K page filled with random data
uint8_t* rps::SrpV3Server::allocatePage(uint64_t addr4k) {
    uint8_t* page = reinterpret_cast<uint8_t*>(malloc(0x1000));
    if (page == nullptr) {
        log_->error("Failed to allocate page at 0x%" PRIx64, addr4k);
        return nullptr;
    }

    // Fill with random data to emulate uninitialized hardware memory
    std::mt19937 gen(std::random_device{}());
    uint32_t* p32 = reinterpret_cast<uint32_t*>(page);
    for (size_t i = 0; i < 0x1000 / 4; i++) p32[i] = gen();

    memMap_.insert(std::make_pair(addr4k, page));
    totAlloc_++;
    log_->debug("Allocating page at 0x%" PRIx64 ". Total pages %" PRIu32, addr4k, totAlloc_);
    return page;
}

//! Read from internal memory
void rps::SrpV3Server::readMemory(uint64_t address, uint8_t* data, uint32_t size) {
    uint64_t addr4k;
    uint64_t off4k;
    uint64_t size4k;

    while (size > 0) {
        addr4k = (address / 0x1000) * 0x1000;
        off4k  = address % 0x1000;
        size4k = (addr4k + 0x1000) - (addr4k + off4k);

        if (size4k > size) size4k = size;

        auto it = memMap_.find(addr4k);
        if (it == memMap_.end()) {
            // Allocate page with random data on first read (like uninitialized SRAM)
            uint8_t* page = allocatePage(addr4k);
            if (page == nullptr) return;
            memcpy(data, page + off4k, size4k);
        } else {
            memcpy(data, it->second + off4k, size4k);
        }

        size -= size4k;
        address += size4k;
        data += size4k;
    }
}

//! Write to internal memory
void rps::SrpV3Server::writeMemory(uint64_t address, const uint8_t* data, uint32_t size) {
    uint64_t addr4k;
    uint64_t off4k;
    uint64_t size4k;

    while (size > 0) {
        addr4k = (address / 0x1000) * 0x1000;
        off4k  = address % 0x1000;
        size4k = (addr4k + 0x1000) - (addr4k + off4k);

        if (size4k > size) size4k = size;

        auto it = memMap_.find(addr4k);
        if (it == memMap_.end()) {
            uint8_t* page = allocatePage(addr4k);
            if (page == nullptr) return;
            it = memMap_.find(addr4k);
        }

        memcpy(it->second + off4k, data, size4k);

        size -= size4k;
        address += size4k;
        data += size4k;
    }
}

//! Queue an incoming frame for processing
void rps::SrpV3Server::acceptFrame(ris::FramePtr frame) {
    {
        std::lock_guard<std::mutex> lock(queMtx_);
        queue_.push(frame);
    }
    queCond_.notify_one();
}

//! Process a single request frame
void rps::SrpV3Server::processFrame(ris::FramePtr frame) {
    uint32_t header[HeadLen / 4];
    uint32_t tail[TailLen / 4];
    uint32_t fSize;
    uint32_t opCode;
    uint32_t id;
    uint64_t address;
    uint32_t reqSize;
    bool doWrite;
    bool isPost;

    rogue::GilRelease noGil;
    ris::FrameLockPtr frLock = frame->lock();

    if (frame->getError()) {
        log_->warning("Got errored frame = 0x%" PRIx8, frame->getError());
        return;
    }

    // Check minimum frame size
    fSize = frame->getPayload();
    if (fSize < HeadLen) {
        log_->warning("Got undersized frame size = %" PRIu32, fSize);
        return;
    }

    // Read header
    ris::FrameIterator fIter = frame->begin();
    ris::fromFrame(fIter, HeadLen, header);

    // Verify SRPv3 version
    if ((header[0] & 0xFF) != 0x03) {
        log_->warning("Got non-SRPv3 frame, version = 0x%" PRIx32, header[0] & 0xFF);
        return;
    }

    // Extract fields
    opCode  = (header[0] >> 8) & 0x3;
    id      = header[1];
    address = (static_cast<uint64_t>(header[3]) << 32) | header[2];
    reqSize = header[4] + 1;

    // Validate opCode: 0=read, 1=write, 2=posted write
    if (opCode == 0x3) {
        log_->warning("Got invalid SRPv3 opcode 0x3 for id=%" PRIu32, id);
        return;
    }

    doWrite = (opCode == 0x1);  // Write
    isPost  = (opCode == 0x2);  // Posted write

    log_->debug("Got request id=%" PRIu32 ", opCode=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32,
                id,
                opCode,
                address,
                reqSize);

    // Release the incoming frame lock before building/sending response
    frLock.reset();

    {
        std::lock_guard<std::mutex> lock(memMtx_);

        if (doWrite || isPost) {
            // Verify frame contains write data
            if (fSize < HeadLen + reqSize) {
                log_->warning("Write frame too small: got %" PRIu32 ", need %" PRIu32, fSize, HeadLen + reqSize);
                return;
            }

            // Re-lock and read write data from frame
            frLock = frame->lock();
            fIter  = frame->begin() + HeadLen;
            std::vector<uint8_t> wrData(reqSize);
            ris::fromFrame(fIter, reqSize, wrData.data());
            frLock.reset();

            writeMemory(address, wrData.data(), reqSize);

            log_->debug("Write complete id=%" PRIu32 ", addr=0x%" PRIx64 ", size=%" PRIu32, id, address, reqSize);
        }

        // Posted writes do not get a response
        if (isPost) return;

        // Build response frame
        uint32_t respLen          = HeadLen + reqSize + TailLen;
        ris::FramePtr respFrame   = reqFrame(respLen, true);
        respFrame->setPayload(respLen);
        ris::FrameIterator rIter  = respFrame->begin();

        // Write header (echo back the request header)
        ris::toFrame(rIter, HeadLen, header);

        // Write data payload (read from internal memory)
        std::vector<uint8_t> rdData(reqSize);
        readMemory(address, rdData.data(), reqSize);
        ris::toFrame(rIter, reqSize, rdData.data());

        // Write tail (status = 0 = success)
        tail[0] = 0;
        ris::toFrame(rIter, TailLen, tail);

        log_->debug("Sending response id=%" PRIu32 ", size=%" PRIu32, id, respLen);

        sendFrame(respFrame);
    }
}
