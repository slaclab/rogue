/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Class to coordinate data file writing.
 *    This class supports multiple stream slaves, each with the ability to
 *    write to a common data file. The data file is a series of banks.
 *    Each bank has a channel and frame flags. The channel is per source and the
 *    lower 24 bits of the frame flags are used as the flags.
 *    The bank is proceeded by 2 - 32-bit headers to indicate bank information
 *    and length:
 *
 *       headerA:
 *          [31:0] = Length of data block in bytes
 *       headerB
 *          31:24  = Channel ID
 *          23:16  = Frame error
 *          15:0   = Frame flags
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
#include "rogue/Directives.h"

#include "rogue/utilities/fileio/StreamWriter.h"

#include <chrono>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <sys/time.h>
#include <unistd.h>

#include <cstring>
#include <map>
#include <memory>
#include <string>
#include <thread>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/utilities/fileio/StreamWriterChannel.h"

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Class creation
ruf::StreamWriterPtr ruf::StreamWriter::create() {
    ruf::StreamWriterPtr s = std::make_shared<ruf::StreamWriter>();
    return (s);
}

//! Setup class in python
void ruf::StreamWriter::setup_python() {
#ifndef NO_PYTHON
    bp::class_<ruf::StreamWriter, ruf::StreamWriterPtr, boost::noncopyable>("StreamWriter", bp::init<>())
        .def("open", &ruf::StreamWriter::open)
        .def("close", &ruf::StreamWriter::close)
        .def("isOpen", &ruf::StreamWriter::isOpen)
        .def("setRaw", &ruf::StreamWriter::setRaw)
        .def("getRaw", &ruf::StreamWriter::getRaw)
        .def("setBufferSize", &ruf::StreamWriter::setBufferSize)
        .def("setMaxSize", &ruf::StreamWriter::setMaxSize)
        .def("setDropErrors", &ruf::StreamWriter::setDropErrors)
        .def("getChannel", &ruf::StreamWriter::getChannel)
        .def("getTotalSize", &ruf::StreamWriter::getTotalSize)
        .def("getCurrentSize", &ruf::StreamWriter::getCurrentSize)
        .def("getBandwidth", &ruf::StreamWriter::getBandwidth)
        .def("getFrameCount", &ruf::StreamWriter::getFrameCount)
        .def("waitFrameCount", &ruf::StreamWriter::waitFrameCount);
#endif
}

//! Creator
ruf::StreamWriter::StreamWriter() {
    baseName_   = "";
    fd_         = -1;
    sizeLimit_  = 0;
    buffSize_   = 0;
    currSize_   = 0;
    totSize_    = 0;
    buffer_     = NULL;
    frameCount_ = 0;
    bandwidthBytes_ = 0;
    currBuffer_ = 0;
    dropErrors_ = false;
    isOpen_     = false;
    raw_        = false;

    log_ = rogue::Logging::create("fileio.StreamWriter");
}

//! Deconstructor
ruf::StreamWriter::~StreamWriter() {
    this->close();
}

//! Open a data file
void ruf::StreamWriter::open(std::string file) {
    std::string name;

    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    isOpen_ = false;
    flush();

    // Close if open
    if (fd_ >= 0) ::close(fd_);
    fd_ = -1;

    baseName_ = file;
    name      = file;
    fdIdx_    = 1;

    if (sizeLimit_ > 0) name.append(".1");

    if ((fd_ = ::open(name.c_str(),
                      O_RDWR | O_CREAT,
                      S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH)) < 0)
        throw(rogue::GeneralError::create("StreamWriter::open", "Failed to open data file: %s", name.c_str()));

    totSize_    = 0;
    currSize_   = 0;
    frameCount_ = 0;
    bandwidthBytes_ = 0;
    bandwidthHistory_.clear();
    currBuffer_ = 0;

    // Iterate over all channels and reset their frame counts
    for (std::map<uint32_t, ruf::StreamWriterChannelPtr>::iterator it = channelMap_.begin(); it != channelMap_.end();
         ++it) {
        it->second->setFrameCount(0);
    }
    isOpen_ = true;
}

//! Close a data file
void ruf::StreamWriter::close() {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    isOpen_ = false;
    flush();
    bandwidthBytes_ = 0;
    bandwidthHistory_.clear();
    if (fd_ >= 0) ::close(fd_);
    fd_ = -1;
}

//! Get open status
bool ruf::StreamWriter::isOpen() {
    return (isOpen_);
}

//! Set raw mode
void ruf::StreamWriter::setRaw(bool raw) {
   raw_ = raw;
}

//! Get raw mode flag
bool ruf::StreamWriter::getRaw() {
   return raw_;
}

//! Set buffering size, 0 to disable
void ruf::StreamWriter::setBufferSize(uint32_t size) {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);

    // No change
    if (size != buffSize_) {
        // Flush data out of current buffer
        flush();

        // Free old buffer
        if (buffer_ != NULL) free(buffer_);
        buffSize_ = 0;

        // Buffer is enabled
        if (size != 0) {
            // Create new buffer
            if ((buffer_ = reinterpret_cast<uint8_t*>(malloc(size))) == NULL)
                throw(rogue::GeneralError::create("StreamWriter::setBufferSize",
                                                  "Failed to allocate buffer with size = %" PRIu32,
                                                  size));
            buffSize_ = size;
        }
    }
}

//! Set max file size, 0 for unlimited
void ruf::StreamWriter::setMaxSize(uint64_t size) {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    sizeLimit_ = size;
}

//! Set drop errors flag
void ruf::StreamWriter::setDropErrors(bool drop) {
    dropErrors_ = drop;
}

//! Get a slave port
ruf::StreamWriterChannelPtr ruf::StreamWriter::getChannel(uint8_t channel) {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    if (channelMap_.count(channel) == 0) {
        channelMap_[channel] = ruf::StreamWriterChannel::create(shared_from_this(), channel);
    }
    return (channelMap_[channel]);
}

//! Get total file size
uint64_t ruf::StreamWriter::getTotalSize() {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    return (totSize_ + currBuffer_);
}

//! Get current file size
uint64_t ruf::StreamWriter::getCurrentSize() {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    return (currSize_ + currBuffer_);
}

//! Get instantaneous bandwidth in bytes per second over the last second
double ruf::StreamWriter::getBandwidth() {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);

    auto now = std::chrono::steady_clock::now();
    pruneBandwidth(now);

    if (bandwidthHistory_.empty()) return (0.0);

    auto windowStart = bandwidthHistory_.front().first;
    double seconds   = std::chrono::duration<double>(now - windowStart).count();
    if (seconds <= 0.0) return (static_cast<double>(bandwidthBytes_));
    return (static_cast<double>(bandwidthBytes_) / seconds);
}

//! Get current frame count
uint32_t ruf::StreamWriter::getFrameCount() {
    return (frameCount_);
}

bool ruf::StreamWriter::waitFrameCount(uint32_t count, uint64_t timeout) {
    struct timeval endTime;
    struct timeval sumTime;
    struct timeval curTime;

    rogue::GilRelease noGil;
    std::unique_lock<std::mutex> lock(mtx_);

    if (timeout != 0) {
        gettimeofday(&curTime, NULL);

        div_t divResult = div(timeout, 1000000);
        sumTime.tv_sec  = divResult.quot;
        sumTime.tv_usec = divResult.rem;

        timeradd(&curTime, &sumTime, &endTime);
    }

    while (frameCount_ < count) {
        cond_.wait_for(lock, std::chrono::microseconds(1000));

        if (timeout != 0) {
            gettimeofday(&curTime, NULL);
            if (timercmp(&curTime, &endTime, >)) break;
        }
    }

    return (frameCount_ >= count);
}

void ruf::StreamWriter::pruneBandwidth(std::chrono::steady_clock::time_point now) {
    auto cutoff = now - std::chrono::seconds(1);
    while (!bandwidthHistory_.empty() && bandwidthHistory_.front().first < cutoff) {
        bandwidthBytes_ -= bandwidthHistory_.front().second;
        bandwidthHistory_.pop_front();
    }
}

void ruf::StreamWriter::recordBandwidth(uint32_t size) {
    if (size == 0) return;
    auto now = std::chrono::steady_clock::now();
    pruneBandwidth(now);
    bandwidthHistory_.emplace_back(now, size);
    bandwidthBytes_ += size;
}

//! Write data to file. Called from StreamWriterChannel
void ruf::StreamWriter::writeFile(uint8_t channel, std::shared_ptr<rogue::interfaces::stream::Frame> frame) {
    ris::Frame::BufferIterator it;
    uint32_t value;
    uint32_t size;

    if ((frame->getPayload() == 0) || (dropErrors_ && (frame->getError() != 0))) return;

    rogue::GilRelease noGil;
    std::unique_lock<std::mutex> lock(mtx_);

    if (fd_ >= 0) {
        // Raw mode
        if ( raw_ ) {
           size = frame->getPayload();
           checkSize(size);

        // Written size has extra 4 bytes in non raw mode
        // Check file size, including size header
        } else {
           size = frame->getPayload() + 4;
           checkSize(size + 4);
        }

        if (!raw_) {
           // First write size
           intWrite(&size, 4);

           // Create EVIO header
           value = frame->getFlags();
           value |= (frame->getError() << 16);
           value |= (channel << 24);
           intWrite(&value, 4);
        }

        // Write buffers
        for (it = frame->beginBuffer(); it != frame->endBuffer(); ++it) intWrite((*it)->begin(), (*it)->getPayload());

        // Update counters
        frameCount_++;
        cond_.notify_all();
    }
}

//! Internal method for file writing with buffer and auto close and reopen
void ruf::StreamWriter::intWrite(void* data, uint32_t size) {
    if (fd_ < 0) return;

    // New size is larger than buffer size, flush
    if ((size + currBuffer_) > buffSize_) flush();

    // Attempted write is larger than buffer, raw write
    // This is called if buffer is disabled
    if (size > buffSize_) {
        if (write(fd_, data, size) != static_cast<int32_t>(size)) {
            ::close(fd_);
            fd_ = -1;
            log_->error("Write failed, closing file!");
            return;
        }
        currSize_ += size;
        totSize_ += size;
        // Append to buffer if non zero
    } else if (buffSize_ > 0 && size > 0) {
        std::memcpy(buffer_ + currBuffer_, data, size);
        currBuffer_ += size;
    }

    recordBandwidth(size);
}

//! Check file size for next write
void ruf::StreamWriter::checkSize(uint32_t size) {
    std::string name;

    // No Limit
    if (sizeLimit_ == 0) return;

    // Bad configuration
    if (size > sizeLimit_)
        throw(rogue::GeneralError("StreamWriter::checkSize", "Frame size is larger than file size limit"));

    // File size (including buffer) is larger than max size
    if ((size + currBuffer_ + currSize_) > sizeLimit_) {
        flush();

        // Close and update index
        ::close(fd_);
        fdIdx_++;

        name = baseName_ + "." + std::to_string(fdIdx_);

        // Open new file
        if ((fd_ = ::open(name.c_str(),
                          O_RDWR | O_CREAT | O_APPEND,
                          S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH)) < 0)
            throw(rogue::GeneralError::create("StreamWriter::checkSize", "Failed to open file %s", name.c_str()));

        currSize_ = 0;
    }
}

//! Flush file
void ruf::StreamWriter::flush() {
    if (currBuffer_ > 0) {
        if (write(fd_, buffer_, currBuffer_) != static_cast<int32_t>(currBuffer_)) {
            ::close(fd_);
            fd_ = -1;
            log_->error("Write failed, closing file!");
            currBuffer_ = 0;
            return;
        }
        currSize_ += currBuffer_;
        totSize_ += currBuffer_;
        currBuffer_ = 0;
    }
}
