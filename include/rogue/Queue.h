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
    uint32_t max_   = 0;
    uint32_t thold_ = 0;
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
     * `0` disables the depth limit.
     *
     * @param max Maximum queued entries.
     */
    void setMax(uint32_t max) {
        max_ = max;
    }

    /**
     * @brief Sets busy-threshold depth used by `busy()`.
     * @param thold Queue depth threshold.
     */
    void setThold(uint32_t thold) {
        thold_ = thold;
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
