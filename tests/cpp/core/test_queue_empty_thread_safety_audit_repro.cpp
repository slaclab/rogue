/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Pinning the rogue::Queue<T> thread-safety contract.  The file is split into
 * two layers, both required.
 *
 * Layer A — source-text audit (deterministic, no scheduling).  Four
 * structural invariants are enforced against include/rogue/Queue.h after the
 * raw text is run through stripCommentsAndLiterals(), so signature lookup,
 * brace counting, and the lock-token grep all operate on executable code
 * only.  A doc-only edit to Queue.h cannot disturb the audit, and a stray
 * `{` / `}` / signature spelling in a comment cannot fool the parser.
 *
 *   1. Queue::empty() acquires mtx_ before reading queue_.
 *      All other queue mutators (push/pop/reset) and accessors (size) take
 *      the lock; empty() must do the same.  A previous revision returned
 *      queue_.empty() lock-free, which a concurrent push() could observe
 *      mid-mutation — non-thread-safe and UB-flavoured under the C++ memory
 *      model.
 *
 *   2. max_ and thold_ are declared as std::atomic<uint32_t>.
 *      push()/pop() read these members under mtx_; the setters now also
 *      write them under mtx_, so on the steady-state code path the same
 *      mutex serializes both sides.  The atomic<> declaration is kept as
 *      API-level defence in depth: setMax()/setThold() are public, the
 *      contract does not forbid runtime use, and any future lock-free
 *      reader (or a regression that reverts the setter lock) would
 *      reintroduce a data race.  The current in-tree callers happen to
 *      invoke the setters early enough that no concurrent reader runs,
 *      so they do not exercise a real race today — but the contract has
 *      to make the runtime case well-defined regardless.
 *
 *   3. setMax() acquires mtx_ and notifies pushCond_.notify_all after
 *      updating max_.
 *      The lock is required to synchronize with push()'s predicate
 *      evaluation — without it the store can land between a producer's
 *      max_ read and its pushCond_.wait(), making notify_all() a no-op
 *      (no waiter yet) and leaving the producer asleep on the old cap
 *      until an unrelated pop()/stop() — a classic check→wait lost-wakeup
 *      race.  The notify must specifically be notify_all (not notify_one):
 *      push() itself only issues popCond_.notify_all() on success, so a
 *      notify_one() regression would wake one of N blocked producers and
 *      strand the remaining N-1 until an unrelated pop()/stop().  All
 *      structural lock checks (this case, empty, size, setThold) require
 *      the lock primitive's *constructor* to take (mtx_) in the same
 *      statement, so locking an unrelated mutex no longer satisfies the
 *      audit even if (mtx_) appears elsewhere in the body.
 *
 *   4. setThold() acquires mtx_ and recomputes busy_.
 *      busy() reads a cached busy_ flag that depends on both thold_ and
 *      queue_.size(); without recomputing under the lock, changing the
 *      threshold at runtime leaves busy() reporting the previous state
 *      until the next push()/pop()/reset().
 *
 * Trade-off: the source-text checks are intentionally tied to the *spelling*
 * of the fix and would not catch an equivalent fix that delegates locking
 * to a helper or wraps the atomics in a typedef.  That is acceptable for an
 * audit-style regression: the cost of detecting the specific revert that
 * originally broke the contract outweighs the cost of a false negative on
 * a hypothetical re-spelling, which would still need a deliberate human
 * change.
 *
 * Layer B — behavioural tests for the runtime contracts the source-text
 * audit cannot prove on its own.  Layer B is observational: there is no
 * public hook inside Queue::push() that signals when pushCond_.wait() is
 * reached, so "producer is parked in wait()" can only be inferred from
 * outside via sustained absence of progress + sustained reachability of
 * mtx_ via q.size().  See the per-TEST_CASE comments below for the
 * specific handshake.  Layer A's structural audit is the deterministic
 * regression catch for the spelled invariants (locked setter, notify_all,
 * recompute against queue_.size()); Layer B catches the visible runtime
 * breakage (no wakeup at all, multi-waiter starvation, stale busy()) with
 * high but not perfect probability.  The two layers are complementary.
 *
 *   5. Changing the cap with setMax() wakes a producer already blocked in
 *      push() rather than leaving it asleep until an unrelated pop()/stop().
 *      Two SUBCASEs cover both runtime paths: setMax(10) (raise) and
 *      setMax(0) (the documented "no limit" special case that disables
 *      the cap entirely).  This exercises the runtime wakeup contract
 *      that locked + notify_all establishes; a regression that drops the
 *      lock or the notify would let the producer time out instead of
 *      completing the push.
 *
 *   6. setMax() raising the cap wakes ALL blocked producers.
 *      The single-producer test in case 5 cannot distinguish notify_all
 *      from notify_one.  This case spawns N=4 blocked producers, raises
 *      the cap to fit all of them, and asserts every one completes —
 *      catching a regression to pushCond_.notify_one() that would only
 *      wake one and strand the rest (push() does not chain pushCond_
 *      notifications, so subsequent waiters never wake on their own).
 *
 *   7. Calling setThold() flips busy() immediately against the current
 *      queue depth — without recomputing busy_ at setThold() time the flag
 *      would only update on the next push()/pop()/reset().  Includes the
 *      documented setThold(0) "no threshold" special case (busy() must
 *      stay false even when the queue is non-empty), so a regression that
 *      drops the (thold > 0) guard from the recompute is caught.  Purely
 *      deterministic; no threading required.
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
#include <cstddef>
#include <fstream>
#include <iterator>
#include <string>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/Queue.h"

namespace {

std::string readFile(const std::string& path) {
    std::ifstream f(path);
    if (!f.is_open()) return "";
    return std::string((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
}

// Removes comments and string/char literals so audits only inspect executable text.
std::string stripCommentsAndLiterals(const std::string& src) {
    std::string out;
    out.reserve(src.size());

    enum State { CODE, LINE_COMMENT, BLOCK_COMMENT, STRING_LIT, CHAR_LIT };
    State st = CODE;

    for (std::size_t i = 0; i < src.size(); ++i) {
        char c    = src[i];
        char next = (i + 1 < src.size()) ? src[i + 1] : '\0';

        switch (st) {
            case CODE:
                if (c == '/' && next == '/') {
                    st = LINE_COMMENT;
                    ++i;
                } else if (c == '/' && next == '*') {
                    st = BLOCK_COMMENT;
                    ++i;
                } else if (c == '"') {
                    st = STRING_LIT;
                } else if (c == '\'') {
                    st = CHAR_LIT;
                } else {
                    out.push_back(c);
                }
                break;
            case LINE_COMMENT:
                if (c == '\n') {
                    st = CODE;
                    out.push_back(c);
                }
                break;
            case BLOCK_COMMENT:
                if (c == '*' && next == '/') {
                    st = CODE;
                    ++i;
                }
                break;
            case STRING_LIT:
                if (c == '\\' && next != '\0') {
                    ++i;  // skip escaped char
                } else if (c == '"') {
                    st = CODE;
                }
                break;
            case CHAR_LIT:
                if (c == '\\' && next != '\0') {
                    ++i;
                } else if (c == '\'') {
                    st = CODE;
                }
                break;
        }
    }
    return out;
}

std::string loadStrippedQueueHeader() {
    return stripCommentsAndLiterals(readFile(std::string(ROGUE_SRC_DIR) + "/include/rogue/Queue.h"));
}

// Extract method body (brace-counted) from comment-stripped source.
std::string extractMethodBody(const std::string& src, const std::string& method_prefix) {
    std::size_t pos = src.find(method_prefix);
    if (pos == std::string::npos) return "";

    // Advance to the opening brace of the method body.
    std::size_t brace_start = src.find('{', pos);
    if (brace_start == std::string::npos) return "";

    int depth = 0;
    std::size_t i   = brace_start;
    for (; i < src.size(); ++i) {
        if (src[i] == '{') {
            ++depth;
        } else if (src[i] == '}') {
            --depth;
            if (depth == 0) {
                // i is the closing brace of the method body.
                return src.substr(pos, i - pos + 1);
            }
        }
    }
    // Malformed source — return what we have.
    return src.substr(pos, i - pos);
}

// Position of the first lock_guard/unique_lock statement that takes (mtx_).
std::size_t findLockPos(const std::string& code) {
    std::size_t best = std::string::npos;
    static const std::string tokens[] = {"unique_lock<", "lock_guard<"};
    for (const auto& tok : tokens) {
        std::size_t pos = 0;
        while ((pos = code.find(tok, pos)) != std::string::npos) {
            const std::size_t stmt_end = code.find(';', pos);
            if (stmt_end == std::string::npos) break;
            if (code.substr(pos, stmt_end - pos).find("(mtx_)") != std::string::npos) {
                if (pos < best) best = pos;
                break;  // earliest match for this token; later tokens are larger.
            }
            pos = stmt_end + 1;
        }
    }
    return best;
}

bool locksMtx(const std::string& code) {
    return findLockPos(code) != std::string::npos;
}

// Position of the first `lhs = ...` assignment (excludes comparisons and substrings).
std::size_t findAssignPos(const std::string& code, const std::string& lhs) {
    auto isIdentChar = [](char c) {
        return (c == '_') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9');
    };
    std::size_t pos = 0;
    while ((pos = code.find(lhs, pos)) != std::string::npos) {
        const bool boundary_ok = (pos == 0) || !isIdentChar(code[pos - 1]);
        if (boundary_ok) {
            std::size_t i = pos + lhs.size();
            while (i < code.size() && (code[i] == ' ' || code[i] == '\t' || code[i] == '\n' || code[i] == '\r')) {
                ++i;
            }
            if (i < code.size() && code[i] == '=' && (i + 1 >= code.size() || code[i + 1] != '=')) {
                return pos;
            }
        }
        pos += lhs.size();
    }
    return std::string::npos;
}

}  // namespace

TEST_CASE("Queue::empty() acquires mutex before reading queue_") {
    const std::string src = loadStrippedQueueHeader();
    REQUIRE_MESSAGE(!src.empty(),
                    "could not open include/rogue/Queue.h (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    const std::string empty_code = extractMethodBody(src, "bool empty()");
    REQUIRE_MESSAGE(!empty_code.empty(), "could not locate bool empty() in Queue.h");

    const std::string size_code = extractMethodBody(src, "uint32_t size()");
    REQUIRE_MESSAGE(!size_code.empty(), "could not locate uint32_t size() in Queue.h");

    CHECK_MESSAGE(locksMtx(size_code),
                  "reference check failed — size() does not take mtx_; "
                  "the test assumption about the reference implementation is wrong.");

    CHECK_MESSAGE(locksMtx(empty_code),
                  "Queue::empty() body lacks std::unique_lock<std::mutex> lock(mtx_) "
                  "or std::lock_guard<std::mutex> lock(mtx_); it reads queue_.empty() "
                  "without holding mtx_ while push()/pop() both take the lock. "
                  "Concurrent push+empty() can observe an inconsistent queue state "
                  "(not thread-safe).");

    // Lock must precede the queue_.empty() read.
    const std::size_t lock_pos = findLockPos(empty_code);
    const std::size_t read_pos = empty_code.find("queue_.empty()");
    const bool   ordered  = (lock_pos != std::string::npos) && (read_pos != std::string::npos) && (lock_pos < read_pos);
    CHECK_MESSAGE(ordered,
                  "Queue::empty() reads queue_.empty() before acquiring mtx_; "
                  "the lock must precede the read so the observation is taken "
                  "against a stable, mutex-protected queue_ state.");
}

TEST_CASE("Queue::max_ and Queue::thold_ are declared std::atomic<uint32_t>") {
    const std::string src = loadStrippedQueueHeader();
    REQUIRE_MESSAGE(!src.empty(), "could not open include/rogue/Queue.h");

    CHECK_MESSAGE(src.find("std::atomic<uint32_t> max_") != std::string::npos,
                  "Queue::max_ is not declared std::atomic<uint32_t>; "
                  "push()/pop() read it under mtx_ and setMax() writes it "
                  "under mtx_, but the public Queue<T> API does not restrict "
                  "setMax() to construction time. A plain uint32_t leaves any "
                  "future runtime caller (or a regression that drops the "
                  "setter lock) racing the push()/pop() read.");

    CHECK_MESSAGE(src.find("std::atomic<uint32_t> thold_") != std::string::npos,
                  "Queue::thold_ is not declared std::atomic<uint32_t>; "
                  "kept atomic for symmetry with max_ and as defence against "
                  "any future lock-free reader.");
}

TEST_CASE("Queue::setMax() acquires mtx_ and notifies pushCond_") {
    const std::string src = loadStrippedQueueHeader();
    REQUIRE_MESSAGE(!src.empty(), "could not open include/rogue/Queue.h");

    const std::string code = extractMethodBody(src, "void setMax(uint32_t max)");
    REQUIRE_MESSAGE(!code.empty(), "could not locate void setMax(uint32_t max) in Queue.h");

    CHECK_MESSAGE(locksMtx(code),
                  "Queue::setMax() does not acquire mtx_; without the lock the "
                  "store can land between push()'s predicate check and "
                  "pushCond_.wait(), making notify_all() a no-op and leaving the "
                  "producer asleep on the old cap (check→wait lost-wakeup).");

    // Ordering: lock → store max_ → notify_all pushCond_.
    const std::size_t lock_pos   = findLockPos(code);
    const std::size_t store_pos  = findAssignPos(code, "max_");
    const std::size_t notify_pos = code.find("pushCond_.notify_all");

    CHECK_MESSAGE(store_pos != std::string::npos,
                  "Queue::setMax() does not contain a `max_ = ...` assignment; "
                  "the body must store the new value into max_ (a bare read or "
                  "comparison such as `if (max_ == max)` is insufficient).");

    CHECK_MESSAGE(notify_pos != std::string::npos,
                  "Queue::setMax() does not call pushCond_.notify_all() after "
                  "updating max_.  notify_one() is insufficient because push() "
                  "itself only issues popCond_.notify_all() on success, so any "
                  "second/third producer blocked on the old cap would never wake "
                  "until an unrelated pop()/stop().");

    const bool found    = (lock_pos != std::string::npos) && (store_pos != std::string::npos) && (notify_pos != std::string::npos);
    const bool ordered  = found && (lock_pos < store_pos) && (store_pos < notify_pos);
    CHECK_MESSAGE(ordered,
                  "Queue::setMax() body must be ordered as: lock mtx_, store max_, "
                  "notify_all pushCond_.  Storing or notifying out of order (e.g. "
                  "notifying before the store, or storing outside the locked "
                  "region) keeps the check→wait lost-wakeup window open.");
}

TEST_CASE("Queue::setThold() acquires mtx_ and recomputes busy_") {
    const std::string src = loadStrippedQueueHeader();
    REQUIRE_MESSAGE(!src.empty(), "could not open include/rogue/Queue.h");

    const std::string code = extractMethodBody(src, "void setThold(uint32_t thold)");
    REQUIRE_MESSAGE(!code.empty(), "could not locate void setThold(uint32_t thold) in Queue.h");

    CHECK_MESSAGE(locksMtx(code),
                  "Queue::setThold() does not acquire mtx_; recomputing busy_ "
                  "without the lock cannot be made consistent with concurrent "
                  "push()/pop() that also update busy_ under the lock.");

    CHECK_MESSAGE(code.find("busy_") != std::string::npos,
                  "Queue::setThold() does not update busy_; changing the "
                  "threshold at runtime leaves busy() reporting the previous "
                  "state until the next push()/pop()/reset().");

    // Recompute must consult live queue depth, not just touch busy_.
    CHECK_MESSAGE(code.find("queue_.size()") != std::string::npos,
                  "Queue::setThold() does not recompute busy_ against the "
                  "current queue_.size(); a regression that copies the "
                  "previous busy_ value would still pass the bare 'busy_' "
                  "token check while leaving busy() reporting stale state.");
}

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
