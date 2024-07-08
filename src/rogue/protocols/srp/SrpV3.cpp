/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SRP protocol bridge, Version 3
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

#include "rogue/protocols/srp/SrpV3.h"

#include <inttypes.h>
#include <stdint.h>
#include <string.h>

#include <memory>
#include <thread>

#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/interfaces/memory/Transaction.h"
#include "rogue/interfaces/memory/TransactionLock.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rps = rogue::protocols::srp;
namespace rim = rogue::interfaces::memory;
namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
rps::SrpV3Ptr rps::SrpV3::create() {
    rps::SrpV3Ptr p = std::make_shared<rps::SrpV3>();
    return (p);
}

//! Setup class in python
void rps::SrpV3::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rps::SrpV3, rps::SrpV3Ptr, bp::bases<ris::Master, ris::Slave, rim::Slave>, boost::noncopyable>(
        "SrpV3",
        bp::init<>())
        .def("_setHardwareTimeout", &rps::SrpV3::setHardwareTimeout);
    bp::implicitly_convertible<rps::SrpV3Ptr, ris::MasterPtr>();
    bp::implicitly_convertible<rps::SrpV3Ptr, ris::SlavePtr>();
    bp::implicitly_convertible<rps::SrpV3Ptr, rim::SlavePtr>();
#endif
}

//! Creator with version constant
rps::SrpV3::SrpV3() : ris::Master(), ris::Slave(), rim::Slave(4, 4096) {
    log_ = rogue::Logging::create("SrpV3");
}

//! Deconstructor
rps::SrpV3::~SrpV3() {}

//! Set the hardware timeout
void rps::SrpV3::setHardwareTimeout(uint8_t val) {
    timeout_ = val;
}

//! Setup header, return frame size
bool rps::SrpV3::setupHeader(rim::TransactionPtr tran, uint32_t* header, uint32_t& frameLen, bool tx) {
    bool doWrite = true;

    // Bits 7:0 of first 32-bit word are version
    header[0] = 0x03;

    // Bits 9:8: 0x0 = read, 0x1 = write, 0x2 = posted write
    switch (tran->type()) {
        case rim::Write:
            header[0] |= 0x100;
            break;
        case rim::Post:
            header[0] |= 0x200;
            break;
        default:
            doWrite = false;
            break;  // Read or verify
    }

    // Bits 13:10 not used in gen frame
    // Bit 14 = ignore mem resp
    // Bit 23:15 = Unused
    // Bit 31:24 = timeout count
    header[0] |= (timeout_ << 24 | 0x00000000);

    // Header word 1, transaction ID
    header[1] = tran->id();

    // Header word 2, lower address
    header[2] = tran->address() & 0xFFFFFFFF;

    // Header word 3, upper address
    header[3] = (tran->address() >> 32) & 0xFFFFFFFF;

    // Header word 4, request size
    header[4] = tran->size() - 1;

    // Determine frame length
    frameLen = HeadLen;

    // Transmit with write data
    if (tx && doWrite) frameLen += tran->size();

    // Receive frames
    else if (!tx)
        frameLen += tran->size() + TailLen;

    return doWrite;
}

//! Post a transaction
void rps::SrpV3::doTransaction(rim::TransactionPtr tran) {
    ris::FrameIterator fIter;
    rim::Transaction::iterator tIter;
    ris::FramePtr frame;
    uint32_t frameSize;
    uint32_t header[HeadLen / 4];
    bool doWrite;

    // Size error
    if ((tran->address() % min()) != 0) {
        tran->error("Transaction address 0x%" PRIx64 " is not aligned to min size %" PRIu32, tran->address(), min());
        return;
    }

    // Size error
    if ((tran->size() % min()) != 0 || tran->size() < min()) {
        tran->error("Transaction size 0x%" PRIx32 " is not aligned to min size %" PRIu32, tran->size(), min());
        return;
    }

    if (tran->size() > max()) {
        tran->error("Transaction size %" PRIu32 " exceeds max size %" PRIu32, tran->size(), max());
        return;
    }

    // Compute header and frame size
    doWrite = setupHeader(tran, header, frameSize, true);

    // Request frame
    frame = reqFrame(frameSize, true);
    frame->setPayload(frameSize);

    // Setup iterators
    rogue::GilRelease noGil;
    rim::TransactionLockPtr lock = tran->lock();
    fIter                        = frame->begin();
    tIter                        = tran->begin();

    // Write header
    ris::toFrame(fIter, HeadLen, header);

    // Write data
    if (doWrite) ris::toFrame(fIter, tran->size(), tIter);

    if (tran->type() == rim::Post)
        tran->done();
    else
        addTransaction(tran);

    log_->debug("Send frame for id=%" PRIu32 ", addr 0x%0.8" PRIx64 ". Size=%" PRIu32 ", type=%" PRIu32,
                tran->id(),
                tran->address(),
                tran->size(),
                tran->type());
    log_->debug("Send frame for id=%" PRIu32 ", header: 0x%0.8" PRIx32 " 0x%0.8" PRIx32 " 0x%0.8" PRIx32
                " 0x%0.8" PRIx32 " 0x%0.8" PRIx32,
                tran->id(),
                header[0],
                header[1],
                header[2],
                header[3],
                header[4]);

    sendFrame(frame);
}

//! Accept a frame from master
void rps::SrpV3::acceptFrame(ris::FramePtr frame) {
    ris::FrameIterator fIter;
    rim::Transaction::iterator tIter;
    rim::TransactionPtr tran;
    uint32_t header[HeadLen / 4];
    uint32_t expHeader[HeadLen / 4];
    uint32_t expFrameLen;
    uint32_t tail[TailLen / 4];
    uint32_t id;
    bool doWrite;
    uint32_t fSize;

    rogue::GilRelease noGil;
    ris::FrameLockPtr frLock = frame->lock();

    if (frame->getError()) {
        log_->warning("Got errored frame = 0x%" PRIx8, frame->getError());
        return;  // Invalid frame, drop it
    }

    // Check frame size
    if ((fSize = frame->getPayload()) < (HeadLen + TailLen)) {
        log_->warning("Got undersized frame size = %" PRIu32, fSize);
        return;  // Invalid frame, drop it
    }

    // Get the tail
    fIter = frame->end() - TailLen;
    ris::fromFrame(fIter, TailLen, tail);

    // Get the header
    fIter = frame->begin();
    ris::fromFrame(fIter, HeadLen, header);

    // Extract the id
    id = header[1];
    log_->debug("Got frame id=%" PRIu32 ", header: 0x%0.8" PRIx32 " 0x%0.8" PRIx32 " 0x%0.8" PRIx32 " 0x%0.8" PRIx32
                " 0x%0.8" PRIx32 " tail: 0x%0.8" PRIx32,
                id,
                header[0],
                header[1],
                header[2],
                header[3],
                header[4],
                tail[0]);

    // Find Transaction
    if ((tran = getTransaction(id)) == NULL) {
        log_->warning("Failed to find transaction id=%" PRIu32, id);
        return;  // Bad id or post, drop frame
    }

    // Lock transaction
    rim::TransactionLockPtr lock = tran->lock();

    // Transaction expired
    if (tran->expired()) {
        tran->error("Transaction expired: Id=%" PRIu32
                    " (increase root->timeout value if this ID matches a previous timeout message)",
                    id);
        return;
    }
    tIter = tran->begin();

    // Setup expect header and length
    doWrite = setupHeader(tran, expHeader, expFrameLen, false);

    // Check header
    if (((header[0] & 0xFFFFC3FF) != expHeader[0]) || (header[1] != expHeader[1]) || (header[2] != expHeader[2]) ||
        (header[3] != expHeader[3]) || (header[4] != expHeader[4])) {
        log_->warning("Bad header for %" PRIu32, id);
        tran->error("Received SRPV3 message did not match expected protocol");
        return;
    }

    // Check tail
    if (tail[0] != 0) {
        if (tail[0] & 0x2000)
            tran->error("FPGA register bus lockup detected in hardware. Power cycle required.");
        else if (tail[0] & 0x0100)
            tran->error("FPGA register bus timeout detected in hardware");
        else
            tran->error("Non zero status message returned on fpga register bus in hardware: 0x%" PRIx32, tail[0]);
        log_->warning("Error detected for ID id=%" PRIu32 ", tail=0x%0.8" PRIx32, id, tail[0]);
        return;
    }

    // Verify frame size, drop frame
    if ((fSize != expFrameLen) || (header[4] + 1) != tran->size()) {
        log_->warning("Size mismatch id=%" PRIu32 ". fsize=%" PRIu32 ", exp=%" PRIu32 ", tsize=%" PRIu32
                      ", header=%" PRIu32,
                      id,
                      fSize,
                      expFrameLen,
                      tran->size(),
                      header[4] + 1);
        tran->error("Received SRPV3 message had a header size mismatch");
        return;
    }

    // Copy data if read
    if (!doWrite) ris::fromFrame(fIter, tran->size(), tIter);

    tran->done();
}
