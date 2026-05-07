/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Functional thread-safety tests for rogue::Queue<T>:
 *
 *   1. setMax() wakes a producer already blocked in push() rather than leaving
 *      it asleep until an unrelated pop()/stop().  Two SUBCASEs cover both
 *      runtime paths: setMax(10) (raise) and setMax(0) (the documented
 *      "no limit" special case that disables the cap entirely).  A regression
 *      that drops the lock or the notify would let the producer time out
 *      instead of completing the push.
 *
 *   2. setMax() raising the cap wakes ALL blocked producers (notify_all, not
 *      notify_one).  Spawns N=4 blocked producers, raises the cap to fit all
 *      of them, and asserts every one completes — catching a regression to
 *      pushCond_.notify_one() that would only wake one and strand the rest.
 *
 *   3. setThold() flips busy() immediately against the current queue depth —
 *      without recomputing busy_ at setThold() time the flag would only update
 *      on the next push()/pop()/reset().  Includes the documented setThold(0)
 *      "no threshold" special case (busy() must stay false even when the
 *      queue is non-empty).
 *
 * Layer B is observational: there is no public hook inside Queue::push() that
 * signals when pushCond_.wait() is reached, so "producer is parked in wait()"
 * is inferred from outside via sustained absence of progress + sustained
 * reachability of mtx_ via q.size().
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

#include <array>
#include <atomic>
#include <chrono>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/Queue.h"

TEST_CASE("Queue::setMax() wakes a producer blocked in push()") {
    uint32_t new_cap = 0;
    SUBCASE("raising the cap to a larger value") {
        new_cap = 10;
    }
    SUBCASE("disabling the cap with setMax(0)") {
        new_cap = 0;
    }

    rogue::Queue<int> q;
    q.setMax(2);

    q.push(0);
    q.push(1);

    std::atomic<bool> entered{false};
    std::atomic<bool> done{false};

    std::thread producer([&] {
        entered.store(true, std::memory_order_release);
        q.push(2);
        done.store(true, std::memory_order_release);
    });

    bool producer_started = false;
    {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!entered.load(std::memory_order_acquire) &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        producer_started = entered.load(std::memory_order_acquire);
    }

    // Sustained-quiet window: infer producer is parked in pushCond_.wait().
    bool producer_blocked = false;
    if (producer_started) {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(500);
        bool stable = true;
        while (std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
            if (done.load(std::memory_order_acquire)) {
                stable = false;
                break;
            }
            if (q.size() != 2u) {
                stable = false;
                break;
            }
        }
        producer_blocked = stable;
    }

    if (producer_blocked) {
        q.setMax(new_cap);
    }

    bool producer_completed = false;
    {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!done.load(std::memory_order_acquire) &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        producer_completed = done.load(std::memory_order_acquire);
    }

    // Cleanup before assertions to avoid std::terminate on joinable thread.
    if (!producer_completed) {
        q.stop();
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!done.load(std::memory_order_acquire) &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    producer.join();

    REQUIRE(producer_started);
    REQUIRE_MESSAGE(producer_blocked,
                    "Test setup invariant violated: producer completed "
                    "push(2) without ever blocking, even though the queue "
                    "was filled to max_=2 before the producer started.  "
                    "Either the queue accepted a push past its cap (a "
                    "different regression) or the test scaffolding is "
                    "wrong on this runner.");
    CHECK_MESSAGE(producer_completed,
                  "Queue::setMax() did not wake a producer blocked in push() "
                  "after changing the cap.  Either the lock_guard(mtx_) was "
                  "dropped (reopening the check→wait lost-wakeup window) or "
                  "the pushCond_.notify_all() call was dropped (no notifier "
                  "for an already-blocked producer).");
}

TEST_CASE("Queue::setMax() wakes ALL blocked producers (notify_all, not notify_one)") {
    rogue::Queue<int> q;
    q.setMax(2);
    q.push(0);
    q.push(1);

    constexpr int                       N = 4;
    std::array<std::atomic<bool>, N>    started{};  // value-init: all false
    std::atomic<int>                    done{0};

    std::vector<std::thread> producers;
    producers.reserve(N);
    for (int i = 0; i < N; ++i) {
        producers.emplace_back([&, i] {
            started[i].store(true, std::memory_order_release);
            q.push(100 + i);
            done.fetch_add(1, std::memory_order_acq_rel);
        });
    }

    auto count_started = [&]() {
        int c = 0;
        for (int i = 0; i < N; ++i) {
            if (started[i].load(std::memory_order_acquire)) ++c;
        }
        return c;
    };

    bool all_started = false;
    {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (count_started() < N && std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        all_started = (count_started() == N);
    }

    // Sustained-quiet window: infer all producers are parked in pushCond_.wait().
    bool all_blocked = false;
    if (all_started) {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(500);
        bool stable = true;
        while (std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
            if (done.load(std::memory_order_acquire) != 0) {
                stable = false;
                break;
            }
            if (q.size() != 2u) {
                stable = false;
                break;
            }
        }
        all_blocked = stable;
    }

    if (all_blocked) {
        q.setMax(2 + N);
    }

    int completed = 0;
    {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(4);
        while (done.load(std::memory_order_acquire) < N &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        completed = done.load(std::memory_order_acquire);
    }

    if (completed < N) {
        q.stop();
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (done.load(std::memory_order_acquire) < N &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    for (auto& p : producers) p.join();

    REQUIRE(all_started);
    REQUIRE_MESSAGE(all_blocked,
                    "Test setup invariant violated: at least one producer "
                    "completed push() without blocking even though the "
                    "queue was at max_=2 before any producer started.");
    CHECK_MESSAGE(completed == N,
                  "Queue::setMax() raised the cap from 2 to ", (2 + N),
                  " but only ", completed, "/", N,
                  " blocked producers woke.  Likely cause: "
                  "pushCond_.notify_one() instead of notify_all() — "
                  "only one waiter wakes, the rest stay parked because "
                  "push() itself only issues popCond_.notify_all() on "
                  "success (no pushCond_ notify chain).");
}

TEST_CASE("Queue::setThold() flips busy() immediately against the current depth") {
    rogue::Queue<int> q;
    q.push(0);
    q.push(1);
    q.push(2);
    REQUIRE(q.size() == 3u);

    CHECK_FALSE(q.busy());

    q.setThold(10);
    CHECK_FALSE(q.busy());

    q.setThold(3);
    CHECK_MESSAGE(q.busy(),
                  "Queue::setThold() did not recompute busy_ at call time; "
                  "busy() still reports the pre-setThold state.  The "
                  "recompute must consult queue_.size() under mtx_ at the "
                  "moment the threshold changes, not on the next "
                  "push()/pop()/reset().");

    q.setThold(1);
    CHECK(q.busy());

    q.setThold(100);
    CHECK_FALSE(q.busy());

    // setThold(0) disables the threshold; busy() must stay false even with items queued.
    REQUIRE(q.size() == 3u);
    q.setThold(0);
    CHECK_MESSAGE(!q.busy(),
                  "Queue::setThold(0) did not clear busy() — the documented "
                  "'no threshold' special case must keep busy() false even "
                  "when the queue is non-empty.  A likely regression is "
                  "computing busy_ = (queue_.size() >= thold_) without the "
                  "(thold > 0) guard; that satisfies every nonzero threshold "
                  "case above but flips busy() true here.");
}
