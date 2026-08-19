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
#ifndef __ROGUE_PERF_COUNTERS_H__
#define __ROGUE_PERF_COUNTERS_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <atomic>

namespace rogue {
namespace perf {

/** @brief Process-wide count of bytes copied by `toFrame`, `fromFrame`, and
 * `copyFrame`. Always-on, memory_order_relaxed, incremented once per
 * executed `std::memcpy` inside the `FrameIterator.h` copy helpers by the
 * chunk size just moved. */
extern std::atomic<uint64_t> gBufferCopyBytes;

/** @brief Process-wide count of `std::memcpy` calls executed inside
 * `toFrame`, `fromFrame`, and `copyFrame`. Always-on, memory_order_relaxed,
 * incremented once per executed memcpy rather than once per function call,
 * so a frame spanning several buffers counts several copies. */
extern std::atomic<uint64_t> gBufferCopyCount;

/** @brief Process-wide count of `rogue::interfaces::stream::Frame::create()`
 * calls. Always-on, memory_order_relaxed. `Frame` objects do not survive the
 * measured region, so this count is tracked process-wide rather than on a
 * live per-object member. */
extern std::atomic<uint64_t> gFrameCreateCount;

/** @brief Total `FrameLock` acquisitions. Always-on, memory_order_relaxed,
 * incremented at both the constructor's direct lock and the lock() guarded
 * branch, so the ordinary RAII construction path is counted rather than
 * missed. */
extern std::atomic<uint64_t> gFrameLockCount;

/** @brief Process-wide count of `GilRelease::acquire()` calls that actually
 * restore a saved thread state. Always-on, memory_order_relaxed, incremented
 * only inside the `state_ != NULL` branch, so a call that finds nothing to
 * restore does not inflate the count. Defined unconditionally so the getter
 * links (and returns zero) even in a `NO_PYTHON` build, even though the
 * increment site itself only compiles when Python is enabled. */
extern std::atomic<uint64_t> gGilAcquireCount;

/** @brief Process-wide count of `GilRelease::release()` calls that actually
 * save a thread state. Always-on, memory_order_relaxed, incremented only
 * inside the `Py_IsInitialized() && PyGILState_Check()` true branch, so a
 * call made with no GIL held (or no interpreter running) does not count as
 * a crossing. Defined unconditionally so the getter links (and returns
 * zero) even in a `NO_PYTHON` build. */
extern std::atomic<uint64_t> gGilReleaseCount;

/** @brief Process-wide total of bytes returned by every Rogue-issued socket
 * or ZeroMQ send/receive call across the stream TCP core, the memory TCP
 * client and server, and the UDP client and server. Always-on,
 * memory_order_relaxed, added only when the call's returned byte count is
 * non-negative, so a failed call's negative error return never corrupts
 * the total. */
extern std::atomic<uint64_t> gIoBytes;

/** @brief Process-wide count of Rogue-issued socket or ZeroMQ send,
 * receive, or poll calls across the stream TCP core, the memory TCP client
 * and server, and the UDP client and server. Always-on, memory_order_relaxed,
 * incremented once per call the code issues regardless of success or
 * failure, since a failed call is still a call Rogue made. */
extern std::atomic<uint64_t> gIoCallCount;

/** @brief Process-wide count of `ScopedGil` GIL crossings. Always-on,
 * memory_order_relaxed, incremented unconditionally in both the constructor
 * and the destructor, so one scope contributes two crossings, not one.
 * Defined unconditionally so the getter links (and returns zero) even in a
 * `NO_PYTHON` build. */
extern std::atomic<uint64_t> gScopedGilCount;

/** @brief Process-wide count of `rogue::interfaces::memory::Transaction`
 * constructions. Always-on, memory_order_relaxed, incremented in the
 * constructor body itself so both `Transaction::create()` and
 * `createSubTransaction()` (which bypasses `create()` entirely) are
 * counted. */
extern std::atomic<uint64_t> gTransactionCreateCount;

/** @brief Total lock acquisitions across every TransactionLock. Always-on,
 * memory_order_relaxed, incremented at both the constructor's direct lock
 * and the lock() guarded branch. */
extern std::atomic<uint64_t> gTransactionLockCount;

/** @brief Process-wide total of transaction request bytes (`tran->size_`)
 * issued through `Master::intTransaction`. Always-on, memory_order_relaxed. */
extern std::atomic<uint64_t> gTransactionRequestBytes;

/** @brief Process-wide count of transaction requests issued through
 * `Master::intTransaction`, the single chokepoint both `reqTransaction`
 * and `reqTransactionPy` funnel through. Always-on, memory_order_relaxed. */
extern std::atomic<uint64_t> gTransactionRequestCount;

}  // namespace perf

/**
 * @brief Static accessor for process-wide performance counters.
 *
 * @details
 * Every counter here is constructed and destroyed inside the measured
 * region it counts (a lock, a transaction, a frame), so it cannot be
 * attributed to a surviving object the way `Pool::getAllocCount()` can.
 * `PerfCounters` exposes one named getter per metric instead of a bag of
 * stats, matching the per-object getter convention everywhere a surviving
 * object exists.
 */
class PerfCounters {
    PerfCounters() = delete;

  public:
    /** @brief Returns the process-wide buffer-copy byte total. */
    static uint64_t getBufferCopyBytes();

    /** @brief Returns the process-wide buffer-copy memcpy count. */
    static uint64_t getBufferCopyCount();

    /** @brief Returns the process-wide Frame::create() construction count. */
    static uint64_t getFrameCreateCount();

    /** @brief Returns the process-wide FrameLock acquisition count. */
    static uint64_t getFrameLockCount();

    /** @brief Returns the process-wide count of GIL crossings actually
     * restored by GilRelease::acquire(). */
    static uint64_t getGilAcquireCount();

    /** @brief Returns the process-wide count of GIL crossings actually
     * saved by GilRelease::release(). */
    static uint64_t getGilReleaseCount();

    /** @brief Returns the process-wide Rogue-issued I/O byte total. */
    static uint64_t getIoBytes();

    /** @brief Returns the process-wide Rogue-issued I/O call count. */
    static uint64_t getIoCallCount();

    /** @brief Returns the process-wide count of ScopedGil crossings (both
     * constructor and destructor). */
    static uint64_t getScopedGilCount();

    /** @brief Returns the process-wide Transaction construction count. */
    static uint64_t getTransactionCreateCount();

    /** @brief Returns the process-wide TransactionLock acquisition count. */
    static uint64_t getTransactionLockCount();

    /** @brief Returns the process-wide transaction request byte total. */
    static uint64_t getTransactionRequestBytes();

    /** @brief Returns the process-wide transaction request count. */
    static uint64_t getTransactionRequestCount();

    /** @brief Registers Python bindings for the performance counters. */
    static void setup_python();
};
}  // namespace rogue

#endif
