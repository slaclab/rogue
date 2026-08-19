/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Process-wide performance counters for the tiered measurement harness.
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

#include "rogue/PerfCounters.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

namespace rogue {
namespace perf {

std::atomic<uint64_t> gBufferCopyBytes{0};
std::atomic<uint64_t> gBufferCopyCount{0};
std::atomic<uint64_t> gFrameCreateCount{0};
std::atomic<uint64_t> gFrameLockCount{0};
std::atomic<uint64_t> gGilAcquireCount{0};
std::atomic<uint64_t> gGilReleaseCount{0};
std::atomic<uint64_t> gIoBytes{0};
std::atomic<uint64_t> gIoCallCount{0};
std::atomic<uint64_t> gScopedGilCount{0};
std::atomic<uint64_t> gTransactionCreateCount{0};
std::atomic<uint64_t> gTransactionLockCount{0};
std::atomic<uint64_t> gTransactionRequestBytes{0};
std::atomic<uint64_t> gTransactionRequestCount{0};

}  // namespace perf
}  // namespace rogue

//! Get the process-wide buffer-copy byte total
uint64_t rogue::PerfCounters::getBufferCopyBytes() {
    return rogue::perf::gBufferCopyBytes.load(std::memory_order_relaxed);
}

//! Get the process-wide buffer-copy memcpy count
uint64_t rogue::PerfCounters::getBufferCopyCount() {
    return rogue::perf::gBufferCopyCount.load(std::memory_order_relaxed);
}

//! Get the process-wide Frame::create() construction count
uint64_t rogue::PerfCounters::getFrameCreateCount() {
    return rogue::perf::gFrameCreateCount.load(std::memory_order_relaxed);
}

//! Get the process-wide FrameLock acquisition count
uint64_t rogue::PerfCounters::getFrameLockCount() {
    return rogue::perf::gFrameLockCount.load(std::memory_order_relaxed);
}

//! Get the process-wide count of GIL crossings actually restored by acquire()
uint64_t rogue::PerfCounters::getGilAcquireCount() {
    return rogue::perf::gGilAcquireCount.load(std::memory_order_relaxed);
}

//! Get the process-wide count of GIL crossings actually saved by release()
uint64_t rogue::PerfCounters::getGilReleaseCount() {
    return rogue::perf::gGilReleaseCount.load(std::memory_order_relaxed);
}

//! Get the process-wide Rogue-issued I/O byte total
uint64_t rogue::PerfCounters::getIoBytes() {
    return rogue::perf::gIoBytes.load(std::memory_order_relaxed);
}

//! Get the process-wide Rogue-issued I/O call count
uint64_t rogue::PerfCounters::getIoCallCount() {
    return rogue::perf::gIoCallCount.load(std::memory_order_relaxed);
}

//! Get the process-wide count of ScopedGil crossings
uint64_t rogue::PerfCounters::getScopedGilCount() {
    return rogue::perf::gScopedGilCount.load(std::memory_order_relaxed);
}

//! Get the process-wide Transaction construction count
uint64_t rogue::PerfCounters::getTransactionCreateCount() {
    return rogue::perf::gTransactionCreateCount.load(std::memory_order_relaxed);
}

//! Get the process-wide TransactionLock acquisition count
uint64_t rogue::PerfCounters::getTransactionLockCount() {
    return rogue::perf::gTransactionLockCount.load(std::memory_order_relaxed);
}

//! Get the process-wide transaction request byte total
uint64_t rogue::PerfCounters::getTransactionRequestBytes() {
    return rogue::perf::gTransactionRequestBytes.load(std::memory_order_relaxed);
}

//! Get the process-wide transaction request count
uint64_t rogue::PerfCounters::getTransactionRequestCount() {
    return rogue::perf::gTransactionRequestCount.load(std::memory_order_relaxed);
}

//! Setup class in python
void rogue::PerfCounters::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rogue::PerfCounters, boost::noncopyable>("PerfCounters", bp::no_init)
        .def("getBufferCopyBytes", &rogue::PerfCounters::getBufferCopyBytes)
        .staticmethod("getBufferCopyBytes")
        .def("getBufferCopyCount", &rogue::PerfCounters::getBufferCopyCount)
        .staticmethod("getBufferCopyCount")
        .def("getFrameCreateCount", &rogue::PerfCounters::getFrameCreateCount)
        .staticmethod("getFrameCreateCount")
        .def("getFrameLockCount", &rogue::PerfCounters::getFrameLockCount)
        .staticmethod("getFrameLockCount")
        .def("getGilAcquireCount", &rogue::PerfCounters::getGilAcquireCount)
        .staticmethod("getGilAcquireCount")
        .def("getGilReleaseCount", &rogue::PerfCounters::getGilReleaseCount)
        .staticmethod("getGilReleaseCount")
        .def("getIoBytes", &rogue::PerfCounters::getIoBytes)
        .staticmethod("getIoBytes")
        .def("getIoCallCount", &rogue::PerfCounters::getIoCallCount)
        .staticmethod("getIoCallCount")
        .def("getScopedGilCount", &rogue::PerfCounters::getScopedGilCount)
        .staticmethod("getScopedGilCount")
        .def("getTransactionCreateCount", &rogue::PerfCounters::getTransactionCreateCount)
        .staticmethod("getTransactionCreateCount")
        .def("getTransactionLockCount", &rogue::PerfCounters::getTransactionLockCount)
        .staticmethod("getTransactionLockCount")
        .def("getTransactionRequestBytes", &rogue::PerfCounters::getTransactionRequestBytes)
        .staticmethod("getTransactionRequestBytes")
        .def("getTransactionRequestCount", &rogue::PerfCounters::getTransactionRequestCount)
        .staticmethod("getTransactionRequestCount");
#endif
}
