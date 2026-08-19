/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream memory pool
 *    The function calls in this are a mess! create buffer, allocate buffer, etc
 *    need to be reworked.
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

#include "rogue/interfaces/stream/Pool.h"

#include <inttypes.h>
#include <unistd.h>

#include <memory>
#include <string>

#include "rogue/GeneralError.h"
#include "rogue/GilRelease.h"
#include "rogue/interfaces/stream/Buffer.h"
#include "rogue/interfaces/stream/Frame.h"

namespace ris = rogue::interfaces::stream;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Creator
ris::Pool::Pool() {
    allocMeta_  = 0;
    allocBytes_ = 0;
    allocCount_ = 0;
    allocTotalCount_ = 0;
    allocTotalBytes_ = 0;
    allocPeakBytes_  = 0;
    fixedSize_  = 0;
    poolSize_   = 0;
}

//! Destructor
ris::Pool::~Pool() {
    while (!dataQ_.empty()) {
        free(dataQ_.front());
        dataQ_.pop();
    }
}

//! Get allocated memory
uint32_t ris::Pool::getAllocBytes() {
    return (allocBytes_);
}

//! Get allocated count
uint32_t ris::Pool::getAllocCount() {
    return (allocCount_);
}

//! Get monotonic total allocated bytes
uint64_t ris::Pool::getAllocTotalBytes() {
    return (allocTotalBytes_.load(std::memory_order_relaxed));
}

//! Get monotonic total allocation count
uint64_t ris::Pool::getAllocTotalCount() {
    return (allocTotalCount_.load(std::memory_order_relaxed));
}

//! Get peak live allocated bytes
uint64_t ris::Pool::getAllocPeakBytes() {
    return (allocPeakBytes_.load(std::memory_order_relaxed));
}

//! Accept a frame request. Called from master
/*
 * Pass total size required.
 * Pass flag indicating if zero copy buffers are acceptable
 */
ris::FramePtr ris::Pool::acceptReq(uint32_t size, bool zeroCopyEn) {
    ris::FramePtr ret;
    uint32_t frSize;

    ret    = ris::Frame::create();
    frSize = 0;

    // Buffers may be smaller than frame
    while (frSize < size) ret->appendBuffer(allocBuffer(size, &frSize));
    return (ret);
}

//! Return a buffer
/*
 * Called when this instance is marked as owner of a Buffer entity
 */
void ris::Pool::retBuffer(uint8_t* data, uint32_t meta, uint32_t rawSize) {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);

    if (data != NULL) {
        if (rawSize == fixedSize_ && poolSize_ > dataQ_.size())
            dataQ_.push(data);
        else
            free(data);
    }
    allocBytes_ -= rawSize;
    allocCount_--;
}

void ris::Pool::setup_python() {
#ifndef NO_PYTHON
    bp::class_<ris::Pool, ris::PoolPtr, boost::noncopyable>("Pool", bp::init<>())
        .def("getAllocCount", &ris::Pool::getAllocCount)
        .def("getAllocBytes", &ris::Pool::getAllocBytes)
        .def("getAllocTotalCount", &ris::Pool::getAllocTotalCount)
        .def("getAllocTotalBytes", &ris::Pool::getAllocTotalBytes)
        .def("getAllocPeakBytes", &ris::Pool::getAllocPeakBytes)
        .def("setFixedSize", &ris::Pool::setFixedSize)
        .def("getFixedSize", &ris::Pool::getFixedSize)
        .def("setPoolSize", &ris::Pool::setPoolSize)
        .def("getPoolSize", &ris::Pool::getPoolSize);
#endif
}

//! Set fixed size mode
void ris::Pool::setFixedSize(uint32_t size) {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);

    fixedSize_ = size;
}

//! Get fixed size mode
uint32_t ris::Pool::getFixedSize() {
    return fixedSize_;
}

//! Set buffer pool size
void ris::Pool::setPoolSize(uint32_t size) {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);

    poolSize_ = size;
}

//! Get pool size
uint32_t ris::Pool::getPoolSize() {
    return poolSize_;
}

//! Allocate a buffer passed size
// Buffer container and raw data should be allocated from shared memory pool
ris::BufferPtr ris::Pool::allocBuffer(uint32_t size, uint32_t* total) {
    uint8_t* data;
    uint32_t bAlloc;
    uint32_t bSize;
    uint32_t meta = 0;

    bAlloc = size;
    bSize  = size;

    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    if (fixedSize_ > 0) {
        bAlloc = fixedSize_;
        if (bSize > bAlloc) bSize = bAlloc;
    }

    if (dataQ_.size() > 0) {
        data = dataQ_.front();
        dataQ_.pop();
    } else if ((data = reinterpret_cast<uint8_t*>(malloc(bAlloc))) == NULL) {
        throw(
            rogue::GeneralError::create("Pool::allocBuffer", "Failed to allocate buffer with size = %" PRIu32, bAlloc));
    }

    // Only use lower 24 bits of meta.
    // Upper 8 bits may have special meaning to sub-class
    meta = allocMeta_;
    allocMeta_++;
    allocMeta_ &= 0xFFFFFF;
    allocBytes_ += bAlloc;
    allocCount_++;
    allocTotalCount_.fetch_add(1, std::memory_order_relaxed);
    allocTotalBytes_.fetch_add(bAlloc, std::memory_order_relaxed);

    // allocBytes_ is only mutated under mtx_ (held above), so this
    // compare-exchange loop is defence in depth against a future caller
    // rather than a fix for an observed race.
    uint64_t peakCandidate = allocBytes_;
    uint64_t curPeak       = allocPeakBytes_.load(std::memory_order_relaxed);
    while (peakCandidate > curPeak &&
           !allocPeakBytes_.compare_exchange_weak(curPeak, peakCandidate, std::memory_order_relaxed)) {
    }

    if (total != NULL) *total += bSize;
    return (ris::Buffer::create(shared_from_this(), data, meta, bSize, bAlloc));
}

//! Create a Buffer with passed data
ris::BufferPtr ris::Pool::createBuffer(void* data, uint32_t meta, uint32_t size, uint32_t alloc) {
    ris::BufferPtr buff;

    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);

    buff = ris::Buffer::create(shared_from_this(), data, meta, size, alloc);

    allocBytes_ += alloc;
    allocCount_++;
    allocTotalCount_.fetch_add(1, std::memory_order_relaxed);
    allocTotalBytes_.fetch_add(alloc, std::memory_order_relaxed);

    // allocBytes_ is only mutated under mtx_ (held above), so this
    // compare-exchange loop is defence in depth against a future caller
    // rather than a fix for an observed race.
    uint64_t peakCandidate = allocBytes_;
    uint64_t curPeak       = allocPeakBytes_.load(std::memory_order_relaxed);
    while (peakCandidate > curPeak &&
           !allocPeakBytes_.compare_exchange_weak(curPeak, peakCandidate, std::memory_order_relaxed)) {
    }

    return (buff);
}

//! Track buffer deletion
void ris::Pool::decCounter(uint32_t alloc) {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    allocBytes_ -= alloc;
    allocCount_--;
}
