/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * General queue for Rogue
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
#ifndef __ROGUE_QUEUE_H__
#define __ROGUE_QUEUE_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <atomic>
#include <condition_variable>
#include <mutex>
#include <queue>

namespace rogue {
/**
 * @brief Thread-safe bounded queue with optional busy threshold.
 *
 * @details
 * `Queue<T>` supports producer/consumer usage with blocking `push()`/`pop()`.
 * `setMax()` configures the maximum queued depth before `push()` blocks.
 * `setThold()` configures a busy threshold used by `busy()`.
 * `stop()` wakes blocked waiters and causes subsequent blocking calls to exit.
 */
template <typename T>
class Queue {
  private:
    std::queue<T> queue_;
    mutable std::mutex mtx_;
    std::condition_variable pushCond_;
    std::condition_variable popCond_;
    // max_/thold_ are read inside push()/pop() under mtx_.  setMax() and
    // setThold() are part of the public Queue<T> API and the contract does
    // not restrict them to construction time, so any caller may legitimately
    // invoke them while producers/consumers are running.  The API has to
    // make that runtime case well-defined.
    //
    // Both setters write under mtx_ to synchronize with push()/pop()'s
    // predicate evaluation:
    // - setMax() must hold mtx_ across the store + notify_all on pushCond_,
    //   otherwise the store can land between a producer's predicate check
    //   and its pushCond_.wait(), making notify_all() a no-op (no waiter
    //   yet) and leaving the producer asleep on the old cap until an
    //   unrelated pop()/stop() — a classic check→wait lost-wakeup race.
    // - setThold() holds mtx_ to recompute busy_ against the current queue
    //   depth atomically with the threshold change; without it, busy()
    //   reports the stale pre-threshold-change state until the next
    //   push()/pop()/reset().
    // The members remain std::atomic<uint32_t> as defence in depth against
    // any future lock-free reader and to silence TSan on platforms where
    // the standard library implementation flags the same-mutex pattern.
    std::atomic<uint32_t> max_{0};
    std::atomic<uint32_t> thold_{0};
    std::atomic<bool> busy_{false};
    bool run_ = true;

  public:
    /** @brief Constructs an empty running queue. */
    Queue() = default;

    /**
     * @brief Stops queue operation and wakes blocked producers/consumers.
     */
    void stop() {
        std::unique_lock<std::mutex> lock(mtx_);
        run_ = false;
        pushCond_.notify_all();
        popCond_.notify_all();
    }

    /**
     * @brief Sets maximum queue depth before `push()` blocks.
     *
     * @details
     * `0` disables the depth limit.  Acquires `mtx_` so the store + notify
     * is synchronized with `push()`'s predicate evaluation: without the
     * lock the new value could land between a producer's `max_` read and
     * its `pushCond_.wait()`, making `notify_all()` a no-op (no waiter
     * yet) and leaving the producer asleep on the old cap until an
     * unrelated `pop()`/`stop()` notification — a classic check→wait
     * lost-wakeup race.
     *
     * @param max Maximum queued entries.
     */
    void setMax(uint32_t max) {
        std::lock_guard<std::mutex> lock(mtx_);
        max_ = max;
        pushCond_.notify_all();
    }

    /**
     * @brief Sets busy-threshold depth used by `busy()`.
     *
     * @details
     * `0` disables the busy threshold: while `thold_ == 0`, `busy()` stays
     * `false` regardless of queue depth.  Acquires `mtx_` so the new
     * threshold can be evaluated against the current queue depth and
     * `busy_` updated atomically with the threshold change.  Without this,
     * `busy()` would continue reporting the previous state until the next
     * `push()`/`pop()`/`reset()`.
     *
     * @param thold Queue depth threshold (`0` disables the threshold).
     */
    void setThold(uint32_t thold) {
        std::lock_guard<std::mutex> lock(mtx_);
        thold_ = thold;
        busy_  = (thold > 0 && queue_.size() >= thold);
    }

    /**
     * @brief Pushes one entry, blocking when queue is full.
     * @param data Entry to enqueue.
     */
    void push(T const& data) {
        std::unique_lock<std::mutex> lock(mtx_);

        while (run_ && max_ > 0 && queue_.size() >= max_) pushCond_.wait(lock);

        if (run_) queue_.push(data);
        busy_ = (thold_ > 0 && queue_.size() >= thold_);
        popCond_.notify_all();
    }

    /**
     * @brief Returns whether queue is currently empty.
     * @return `true` when no entries are queued.
     */
    bool empty() {
        std::unique_lock<std::mutex> lock(mtx_);
        return queue_.empty();
    }

    /**
     * @brief Returns current queue depth.
     * @return Number of queued entries.
     */
    uint32_t size() {
        std::unique_lock<std::mutex> lock(mtx_);
        return queue_.size();
    }

    /**
     * @brief Returns busy state based on configured threshold.
     * @return `true` when `thold_ > 0` and queue depth is at/above threshold.
     */
    bool busy() {
        return busy_;
    }

    /**
     * @brief Clears all queued entries and resets busy state.
     */
    void reset() {
        std::unique_lock<std::mutex> lock(mtx_);
        while (!queue_.empty()) queue_.pop();
        busy_ = false;
        pushCond_.notify_all();
    }

    /**
     * @brief Pops one entry, blocking until data is available or stopped.
     * @return Popped entry when running; default-initialized `T` when stopped.
     */
    T pop() {
        T ret;
        std::unique_lock<std::mutex> lock(mtx_);
        while (run_ && queue_.empty()) popCond_.wait(lock);
        if (run_) {
            ret = queue_.front();
            queue_.pop();
        }
        busy_ = (thold_ > 0 && queue_.size() >= thold_);
        pushCond_.notify_all();
        return (ret);
    }
};
}  // namespace rogue

#endif
