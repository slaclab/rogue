/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ tests for memory transaction timeout detection, including a
 * deadline that falls exactly on a whole second (tv_usec == 0).
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
#include <stdint.h>
#include <sys/time.h>

#include <atomic>
#include <memory>
#include <string>
#include <thread>

#include "doctest/doctest.h"
#include "rogue/interfaces/memory/Transaction.h"
#include "rogue/interfaces/memory/TransactionLock.h"
#include "support/test_helpers.h"

namespace rim = rogue::interfaces::memory;

namespace {

// Exposes the protected deadline and wait() so the timeout path can be driven directly.
class DeadlineTransaction : public rim::Transaction {
  public:
    explicit DeadlineTransaction(struct timeval timeout) : rim::Transaction(timeout) {}

    // Arm the timer, then move the deadline into the past on an exact second (tv_usec == 0).
    void armWholeSecondDeadlineInPast() {
        refreshTimer(nullptr);
        struct timeval now;
        gettimeofday(&now, NULL);
        endTime_.tv_sec  = now.tv_sec - 1;
        endTime_.tv_usec = 0;
    }

    std::string waitForResult() {
        return wait();
    }
};

}  // namespace

TEST_CASE("Transaction wait times out when the deadline falls on a whole second") {
    struct timeval timeout = {1, 0};
    auto tran              = std::make_shared<DeadlineTransaction>(timeout);
    tran->armWholeSecondDeadlineInPast();

    std::atomic<bool> returned(false);
    std::string result;
    std::thread waiter([&]() {
        result = tran->waitForResult();
        returned.store(true);
    });

    const bool timedOut = rogue_test::waitUntil([&]() { return returned.load(); }, 1000);

    // Release a wait() that ignored the deadline so the thread can be joined.
    if (!timedOut) {
        auto lock = tran->lock();
        tran->done();
    }
    waiter.join();

    REQUIRE(timedOut);
    CHECK_EQ(result, "Timeout waiting for register transaction " + std::to_string(tran->id()) + " message response.");
}
