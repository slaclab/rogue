/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Class to read data files.
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

#include "rogue/utilities/fileio/StreamReader.h"

#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <sys/stat.h>
#include <unistd.h>

#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <utility>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ruf::StreamReaderPtr ruf::StreamReader::create() {
    ruf::StreamReaderPtr s = std::make_shared<ruf::StreamReader>();
    return (s);
}

//! Setup class in python
void ruf::StreamReader::setup_python() {
#ifndef NO_PYTHON
    bp::class_<ruf::StreamReader, ruf::StreamReaderPtr, bp::bases<ris::Master>, boost::noncopyable>("StreamReader",
                                                                                                    bp::init<>())
        .def("open", &ruf::StreamReader::open)
        .def("close", &ruf::StreamReader::close)
        .def("isOpen", &ruf::StreamReader::isOpen)
        .def("closeWait", &ruf::StreamReader::closeWait)
        .def("isActive", &ruf::StreamReader::isActive);
#endif
}

//! Creator
ruf::StreamReader::StreamReader() {
    // Members default-init in header; dtor is safe before open().
}

//! Deconstructor
ruf::StreamReader::~StreamReader() {
    close();
}

//! Open a data file
void ruf::StreamReader::open(std::string file) {
    rogue::GilRelease noGil;
    // Must NOT hold mtx_ across intClose(): runThread() acquires mtx_ on
    // exit (to clear active_ and notify cond_), so joining the worker
    // while we own mtx_ would deadlock for the same reason close() must
    // not.  Drain any prior reader thread first, then take the lock for
    // the new-file state mutations.
    intClose();
    std::unique_lock<std::mutex> lock(mtx_);

    // Determine if we read a group of files
    if (file.substr(file.find_last_of('.')) == ".1") {
        fdIdx_    = 1;
        baseName_ = file.substr(0, file.find_last_of('.'));
    } else {
        fdIdx_    = 0;
        baseName_ = file;
    }

    if ((fd_ = ::open(file.c_str(), O_RDONLY)) < 0)
        throw(rogue::GeneralError::create("StreamReader::open", "Failed to open data file: %s", file.c_str()));

    active_   = true;
    threadEn_ = true;
    try {
        readThread_ = std::make_unique<std::thread>(&StreamReader::runThread, this);
    } catch (...) {
        active_   = false;
        threadEn_ = false;
        ::close(fd_);
        fd_ = -1;
        throw;
    }

    // Set a thread name
#ifndef __MACH__
    pthread_setname_np(readThread_->native_handle(), "StreamReader");
#endif
}

//! Open file
bool ruf::StreamReader::nextFile() {
    std::unique_lock<std::mutex> lock(mtx_);
    std::string name;

    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    } else {
        return (false);
    }
    if (fdIdx_ == 0) return (false);

    fdIdx_++;
    name = baseName_ + "." + std::to_string(fdIdx_);

    if ((fd_ = ::open(name.c_str(), O_RDONLY)) < 0) return (false);
    return (true);
}

//! Close a data file
void ruf::StreamReader::close() {
    // Must NOT hold mtx_ here: intClose() joins readThread_, and runThread()
    // acquires mtx_ on exit (to clear active_ and notify cond_).  Holding the
    // lock during join() would deadlock.
    rogue::GilRelease noGil;
    intClose();
}

//! Get open status
bool ruf::StreamReader::isOpen() {
    return (fd_ >= 0);
}

//! Close a data file
void ruf::StreamReader::intClose() {
    // Serialise close paths (close(), open()->intClose, ~StreamReader)
    // under closeMtx_ so two concurrent callers cannot both join the
    // same std::thread or both ::close(fd_).  closeMtx_ is intentionally
    // distinct from mtx_ — the worker thread acquires mtx_ on exit, so
    // holding mtx_ across the join() below would deadlock for the same
    // reason close() already had to drop it.
    std::unique_ptr<std::thread> tToJoin;
    {
        std::lock_guard<std::mutex> guard(closeMtx_);
        if (readThread_) {
            threadEn_ = false;
            tToJoin   = std::move(readThread_);
        }
    }
    // Join outside any lock.  Once the worker exits it will (under mtx_)
    // ::close(fd_) and set fd_=-1; that store is observable to this
    // thread after join() returns.
    if (tToJoin) tToJoin->join();

    // Cover the no-thread case where open() failed before creating a
    // worker (or close()/intClose was called on a never-opened reader)
    // and fd_ still holds a valid descriptor.  Re-take closeMtx_ so a
    // second concurrent intClose cannot also see fd_ >= 0 and double-close.
    std::lock_guard<std::mutex> guard(closeMtx_);
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
}

//! Close when done
void ruf::StreamReader::closeWait() {
    rogue::GilRelease noGil;
    std::unique_lock<std::mutex> lock(mtx_);
    while (active_) cond_.wait_for(lock, std::chrono::microseconds(1000));
    intClose();
}

//! Return true when done
bool ruf::StreamReader::isActive() {
    rogue::GilRelease noGil;
    return (active_);
}

//! Thread background
void ruf::StreamReader::runThread() {
    int32_t ret;
    uint32_t size;
    uint32_t meta;
    uint16_t flags;
    uint8_t error;
    uint8_t chan;
    uint32_t bSize;
    bool err;
    ris::FramePtr frame;
    ris::Frame::BufferIterator it;
    char* bData;
    Logging log("streamReader");

    ret = 0;
    err = false;
    do {
        // Read size of each frame
        while ((fd_ >= 0) && (read(fd_, &size, 4) == 4)) {
            if (size == 0) {
                log.warning("Bad size read %" PRIu32, size);
                err = true;
                break;
            }

            // Read flags
            if (read(fd_, &meta, 4) != 4) {
                log.warning("Failed to read flags");
                err = true;
                break;
            }

            // Skip next step if frame is empty
            if (size <= 4) continue;
            size -= 4;

            // Extract meta data
            flags = meta & 0xFFFF;
            error = (meta >> 16) & 0xFF;
            chan  = (meta >> 24) & 0xFF;

            // Upper-bound guard: reject frame sizes that exceed the remaining
            // bytes in the open file. This catches corruption (e.g. a 0xFFFFFFFF
            // size header) without imposing an artificial cap on legitimate
            // round-trip with StreamWriter, whose serialized size header spans
            // the full uint32_t range.
            struct stat st;
            off_t cur = ::lseek(fd_, 0, SEEK_CUR);
            if (cur >= 0 && ::fstat(fd_, &st) == 0 && st.st_size >= cur) {
                uint64_t remaining = static_cast<uint64_t>(st.st_size - cur);
                if (size > remaining) {
                    log.warning("Rejecting oversized frame %" PRIu32 " > %" PRIu64 " remaining file bytes",
                                size,
                                remaining);
                    err = true;
                    break;
                }
            }

            // Request frame
            frame = reqFrame(size, true);
            frame->setFlags(flags);
            frame->setError(error);
            frame->setChannel(chan);
            it = frame->beginBuffer();

            while ((err == false) && (size > 0)) {
                bSize = size;

                // Adjust to buffer size, if necessary
                if (bSize > (*it)->getSize()) bSize = (*it)->getSize();

                if ((ret = read(fd_, (*it)->begin(), bSize)) != bSize) {
                    log.warning("Short read. Ret = %" PRId32 " Req = %" PRIu32 " after %" PRIu32 " bytes",
                                ret,
                                bSize,
                                frame->getPayload());
                    ::close(fd_);
                    fd_ = -1;
                    frame->setError(0x1);
                    err = true;
                } else {
                    (*it)->setPayload(bSize);
                    ++it;  // Next buffer
                }
                size -= bSize;
            }
            sendFrame(frame);
        }
    } while (threadEn_ && (err == false) && nextFile());

    std::unique_lock<std::mutex> lock(mtx_);
    if (fd_ >= 0) ::close(fd_);
    fd_     = -1;
    active_ = false;
    cond_.notify_all();
}
