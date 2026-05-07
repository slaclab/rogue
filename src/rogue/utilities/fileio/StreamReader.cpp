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
    // closeMtx_ serialises lifecycle; distinct from mtx_ to avoid join() deadlock.
    std::lock_guard<std::mutex> closeGuard(closeMtx_);

    intCloseLocked();

    std::unique_lock<std::mutex> lock(mtx_);

    // Determine if we read a group of files
    if (file.substr(file.find_last_of('.')) == ".1") {
        fdIdx_    = 1;
        baseName_ = file.substr(0, file.find_last_of('.'));
    } else {
        fdIdx_    = 0;
        baseName_ = file;
    }

    {
        const int32_t newFd = ::open(file.c_str(), O_RDONLY);
        if (newFd < 0)
            throw(rogue::GeneralError::create("StreamReader::open", "Failed to open data file: %s", file.c_str()));
        fd_.store(newFd);
    }

    {
        struct stat st;
        if (::fstat(fd_.load(), &st) == 0 && S_ISREG(st.st_mode)) {
            fileSize_ = static_cast<int64_t>(st.st_size);
        } else {
            fileSize_ = 0;
        }
    }

    active_.store(true);
    threadEn_ = true;
    try {
        readThread_ = std::make_unique<std::thread>(&StreamReader::runThread, this);
    } catch (...) {
        active_.store(false);
        threadEn_ = false;
        ::close(fd_.load());
        fd_.store(-1);
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

    if (fd_.load() >= 0) {
        ::close(fd_.load());
        fd_.store(-1);
    } else {
        return (false);
    }
    if (fdIdx_ == 0) return (false);

    fdIdx_++;
    name = baseName_ + "." + std::to_string(fdIdx_);

    {
        const int32_t newFd = ::open(name.c_str(), O_RDONLY);
        if (newFd < 0) return (false);
        fd_.store(newFd);
    }

    {
        struct stat st;
        if (::fstat(fd_.load(), &st) == 0 && S_ISREG(st.st_mode)) {
            fileSize_ = static_cast<int64_t>(st.st_size);
        } else {
            fileSize_ = 0;
        }
    }
    return (true);
}

//! Close a data file
void ruf::StreamReader::close() {
    rogue::GilRelease noGil;
    intClose();
}

//! Get open status
bool ruf::StreamReader::isOpen() {
    return (fd_.load() >= 0);
}

//! Close a data file
void ruf::StreamReader::intClose() {
    std::lock_guard<std::mutex> guard(closeMtx_);
    intCloseLocked();
}

//! Close body with closeMtx_ assumed held by caller.
void ruf::StreamReader::intCloseLocked() {
    if (readThread_) {
        threadEn_ = false;
        readThread_->join();
        readThread_.reset();
    }
    if (fd_.load() >= 0) {
        ::close(fd_.load());
        fd_.store(-1);
    }
}

//! Close when done
void ruf::StreamReader::closeWait() {
    rogue::GilRelease noGil;
    // Release mtx_ before intClose() to avoid lock-order inversion with open().
    {
        std::unique_lock<std::mutex> lock(mtx_);
        while (active_.load()) cond_.wait_for(lock, std::chrono::microseconds(1000));
    }
    intClose();
}

//! Return true when done
bool ruf::StreamReader::isActive() {
    rogue::GilRelease noGil;
    return (active_.load());
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
    int64_t filePos = 0;
    do {
        // Read size of each frame
        while ((fd_.load() >= 0) && (read(fd_.load(), &size, 4) == 4)) {
            filePos += 4;
            if (size == 0) {
                log.warning("Bad size read %" PRIu32, size);
                err = true;
                break;
            }

            // Read flags
            if (read(fd_.load(), &meta, 4) != 4) {
                log.warning("Failed to read flags");
                err = true;
                break;
            }
            filePos += 4;

            // Skip next step if frame is empty
            if (size <= 4) continue;
            size -= 4;

            // Extract meta data
            flags = meta & 0xFFFF;
            error = (meta >> 16) & 0xFF;
            chan  = (meta >> 24) & 0xFF;

            // Reject frames larger than remaining file bytes (catches corruption).
            if (fileSize_ > 0 && filePos <= fileSize_) {
                uint64_t remaining = static_cast<uint64_t>(fileSize_ - filePos);
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

                if ((ret = read(fd_.load(), (*it)->begin(), bSize)) != bSize) {
                    log.warning("Short read. Ret = %" PRId32 " Req = %" PRIu32 " after %" PRIu32 " bytes",
                                ret,
                                bSize,
                                frame->getPayload());
                    if (ret > 0) filePos += ret;
                    ::close(fd_.load());
                    fd_.store(-1);
                    frame->setError(0x1);
                    err = true;
                } else {
                    (*it)->setPayload(bSize);
                    filePos += bSize;
                    ++it;  // Next buffer
                }
                size -= bSize;
            }
            sendFrame(frame);
        }
        filePos = 0;
    } while (threadEn_ && (err == false) && nextFile());

    std::unique_lock<std::mutex> lock(mtx_);
    if (fd_.load() >= 0) ::close(fd_.load());
    fd_.store(-1);
    active_.store(false);
    cond_.notify_all();
}
