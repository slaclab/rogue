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

/**
 * @brief Strip C and C++ comments and string/char literals from @p src.
 *
 * @details
 * The audit below treats `unique_lock<` / `lock_guard<` (and a small set of
 * member-name fingerprints like `(mtx_)`, `pushCond_.notify`, `queue_.size()`)
 * as evidence that a method actually does the right thing.  If those tokens
 * appear inside a `// ...` comment, a `/* ... *\/` block, a string literal,
 * or a char literal they look identical to real code to a naïve substring
 * search.  Stripping them up front removes that false-positive surface so
 * every downstream operation (signature lookup, brace counting, grep) only
 * inspects executable text.  This is also why every TEST_CASE consumes the
 * pre-stripped source rather than re-stripping per-body — a `{` / `}` or a
 * spurious signature spelling inside a comment in Queue.h must not be able
 * to fool extractMethodBody() into picking up the wrong range.
 */
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

/**
 * @brief Read Queue.h from ROGUE_SRC_DIR with comments and literals stripped.
 *
 * @details
 * Centralised so every TEST_CASE consumes the same pre-stripped form.  Each
 * call re-reads Queue.h and re-runs stripCommentsAndLiterals(); there is no
 * cross-call cache.  The pre-strip happens before signature lookup or brace
 * counting in the calling TEST_CASE, which is what makes the audit immune to:
 *   - `bool empty()` / `void setMax(uint32_t max)` etc. appearing in a
 *     doxygen comment before the real definition,
 *   - stray `{` or `}` inside a comment or string skewing the brace depth,
 *   - lock/condvar tokens in a comment satisfying a naïve substring check.
 *
 * Queue.h is small and the audit suite has a handful of TEST_CASEs, so the
 * per-call I/O + strip cost is negligible (~microseconds) and not worth a
 * static cache.
 */
std::string loadStrippedQueueHeader() {
    return stripCommentsAndLiterals(readFile(std::string(ROGUE_SRC_DIR) + "/include/rogue/Queue.h"));
}

/**
 * @brief Extract the substring of src that starts at the first occurrence of
 *        @p method_prefix and ends at the matching closing brace of the
 *        method body (brace-counting), so adjacent methods are not included.
 *
 * @details
 * Operates on a comment-and-literal-stripped src.  The function scans forward
 * from method_prefix until it finds the opening '{', then counts braces until
 * depth returns to zero.  Stripping at the file level (see
 * loadStrippedQueueHeader) is what makes this correct on the raw header: a
 * `{` / `}` inside a comment or string in Queue.h cannot perturb the depth
 * counter, and a signature spelling inside a doxygen block cannot redirect
 * the search to the wrong range.
 */
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

/**
 * @brief Position of the first `unique_lock<` / `lock_guard<` instantiation
 *        in @p code whose declaration statement contains `(mtx_)`, or
 *        `std::string::npos` if no such statement exists.
 *
 * @details
 * Scans the body statement by statement (split on `;`).  Starting at each
 * `unique_lock<` / `lock_guard<` token, the helper walks forward to the
 * next `;` and checks whether `(mtx_)` appears in that range.  The
 * returned position is the offset of the first lock-template token whose
 * statement passes that check.
 *
 * Pinning to `(mtx_)` matters for both presence and ordering: a regressed
 * body that takes an unrelated mutex first and leaves a stray `(mtx_)`
 * reference elsewhere (or in a later statement) would otherwise satisfy
 * a naïve "first lock primitive" search and let the protected read /
 * store appear to be properly ordered against an unrelated lock.
 */
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

/**
 * @brief True when @p code contains at least one `unique_lock<` /
 *        `lock_guard<` declaration whose constructor argument is `(mtx_)`.
 *
 * @details
 * Thin wrapper over findLockPos(): the method body locks `mtx_` if and
 * only if findLockPos() finds a qualifying statement.  Using the same
 * underlying scan keeps presence and ordering checks consistent — a
 * regressed body that takes an unrelated mutex (e.g.
 * `lock_guard<std::mutex> lock(other_mtx); use(mtx_);`) cannot satisfy
 * one check without also satisfying the other.
 */
bool locksMtx(const std::string& code) {
    return findLockPos(code) != std::string::npos;
}

/**
 * @brief Position of the first assignment whose left-hand side is the
 *        identifier @p lhs in @p code, or `std::string::npos` if no such
 *        assignment exists.
 *
 * @details
 * Distinguishes assignment from comparison and from substring matches: a
 * naïve `code.find(lhs)` would also fire on `if (lhs == ...)` or on a
 * read like `(void)lhs;`, so an ordering check pinned to that position
 * could be satisfied by a regression that puts the read first and the
 * actual store last (e.g. `if (max_ == max) ...; pushCond_.notify_all();
 * max_ = max;`).
 *
 * Scans the code for occurrences of @p lhs, then for each occurrence
 * verifies (a) the preceding character is not part of an identifier
 * (avoiding e.g. `q_max_` matching when looking for `max_`), and (b) the
 * next non-whitespace character is `=` with the character after that not
 * also `=` (so `lhs ==` does not match).  The returned position is the
 * offset of @p lhs in the matching assignment.
 */
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
    // Read Queue.h (comments/literals stripped) and inspect the empty()
    // method body.
    //
    // Steady-state (post-fix) shape:
    //   bool empty() {
    //       std::unique_lock<std::mutex> lock(mtx_);
    //       return queue_.empty();
    //   }
    //
    // Discriminator: empty() body must contain "unique_lock<" or "lock_guard<"
    // and the (mtx_) constructor-argument fingerprint.

    const std::string src = loadStrippedQueueHeader();
    REQUIRE_MESSAGE(!src.empty(),
                    "could not open include/rogue/Queue.h (ROGUE_SRC_DIR=",
                    ROGUE_SRC_DIR, ")");

    // Extract the empty() and size() method bodies from the stripped source.
    const std::string empty_code = extractMethodBody(src, "bool empty()");
    REQUIRE_MESSAGE(!empty_code.empty(), "could not locate bool empty() in Queue.h");

    const std::string size_code = extractMethodBody(src, "uint32_t size()");
    REQUIRE_MESSAGE(!size_code.empty(), "could not locate uint32_t size() in Queue.h");

    // Reference check: size() must lock mtx_ (this is already true on HEAD).
    CHECK_MESSAGE(locksMtx(size_code),
                  "reference check failed — size() does not take mtx_; "
                  "the test assumption about the reference implementation is wrong.");

    // Primary assertion: empty() must lock mtx_ (not just any mutex).
    CHECK_MESSAGE(locksMtx(empty_code),
                  "Queue::empty() body lacks std::unique_lock<std::mutex> lock(mtx_) "
                  "or std::lock_guard<std::mutex> lock(mtx_); it reads queue_.empty() "
                  "without holding mtx_ while push()/pop() both take the lock. "
                  "Concurrent push+empty() can observe an inconsistent queue state "
                  "(not thread-safe).");

    // Ordering assertion: the lock must be taken *before* queue_.empty() is
    // read.  A regression that reads queue_ first and acquires the lock
    // afterward would still satisfy locksMtx(), so position-test the two.
    // Pre-compute the bool — doctest CHECK_MESSAGE cannot decompose chained
    // `&&` expressions.
    const std::size_t lock_pos = findLockPos(empty_code);
    const std::size_t read_pos = empty_code.find("queue_.empty()");
    const bool   ordered  = (lock_pos != std::string::npos) && (read_pos != std::string::npos) && (lock_pos < read_pos);
    CHECK_MESSAGE(ordered,
                  "Queue::empty() reads queue_.empty() before acquiring mtx_; "
                  "the lock must precede the read so the observation is taken "
                  "against a stable, mutex-protected queue_ state.");
}

TEST_CASE("Queue::max_ and Queue::thold_ are declared std::atomic<uint32_t>") {
    // Read Queue.h (comments/literals stripped) and assert that max_/thold_
    // are atomics.
    //
    // push()/pop() read these members under mtx_, and the setters now also
    // write them under mtx_, so the same mutex serializes both sides on the
    // steady-state code path.  The atomic<> declaration is kept as
    // API-level defence in depth: setMax()/setThold() are public and the
    // contract does not restrict them to construction time, so a future
    // caller (or a regression that drops the setter lock) would create a
    // concurrent non-atomic write/read pair that is UB under the C++ memory
    // model.  Declaring the members atomic makes the worst case well-defined
    // even when the lock is missing.

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
    // setMax() updates the cap that push() waits on.  Two structural
    // invariants are required for correctness:
    //
    //   a. setMax() must hold mtx_ across the store + notify.  push()
    //      evaluates the wait predicate (max_ > 0 && size >= max_) under
    //      mtx_; if setMax() updates max_ lock-free the new value can
    //      land between the predicate check and the pushCond_.wait()
    //      call, so notify_all() fires while the producer is not yet
    //      waiting (no-op) and the producer then sleeps indefinitely
    //      against the old cap — a classic check→wait lost-wakeup.
    //
    //   b. setMax() must call pushCond_.notify_all so *every* producer
    //      already blocked on the old cap re-evaluates against the new
    //      value.  notify_one() is insufficient: push() itself only
    //      issues popCond_.notify_all() on success, so the second/third
    //      blocked producer would never wake until an unrelated
    //      pop()/stop() — multiple-waiter starvation rather than the
    //      single-waiter lost-wakeup the lock closes.

    const std::string src = loadStrippedQueueHeader();
    REQUIRE_MESSAGE(!src.empty(), "could not open include/rogue/Queue.h");

    const std::string code = extractMethodBody(src, "void setMax(uint32_t max)");
    REQUIRE_MESSAGE(!code.empty(), "could not locate void setMax(uint32_t max) in Queue.h");

    CHECK_MESSAGE(locksMtx(code),
                  "Queue::setMax() does not acquire mtx_; without the lock the "
                  "store can land between push()'s predicate check and "
                  "pushCond_.wait(), making notify_all() a no-op and leaving the "
                  "producer asleep on the old cap (check→wait lost-wakeup).");

    // Ordering assertion: the body must lock mtx_, *then* store max_, *then*
    // notify pushCond_.  Notifying before the store (or storing outside the
    // locked region) reintroduces the lost-wakeup race the lock is meant to
    // close, so a bare presence check on `pushCond_.notify` is insufficient.
    // The store position must be the actual `max_ = ...` assignment, not the
    // first `max_` token in the body — otherwise a regression like
    // `if (max_ == max) return; pushCond_.notify_all(); max_ = max;` would
    // pass an ordering check pinned to the comparison's `max_` while leaving
    // the real store after the notify.  findAssignPos() distinguishes
    // assignment from comparison and from substring matches.
    // The notify must specifically be notify_all (not notify_one) so that
    // every producer blocked on the old cap re-evaluates the predicate.
    // Pre-compute the bool — doctest CHECK_MESSAGE cannot decompose chained
    // `&&` expressions.
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
    // setThold() changes the threshold that busy_ is computed from.  Without
    // recomputing busy_ under mtx_ at the same time the threshold changes,
    // busy() keeps reporting the previous state until the next push()/pop().

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

    // Recompute assertion: a bare `busy_` token can be satisfied by
    // assigning the previous value back to itself, which leaves busy()
    // stale until the next push()/pop()/reset().  Requiring `queue_.size()`
    // in the same body forces the recompute to consult the live queue
    // depth (e.g. `busy_ = (thold > 0 && queue_.size() >= thold);`).
    CHECK_MESSAGE(code.find("queue_.size()") != std::string::npos,
                  "Queue::setThold() does not recompute busy_ against the "
                  "current queue_.size(); a regression that copies the "
                  "previous busy_ value would still pass the bare 'busy_' "
                  "token check while leaving busy() reporting stale state.");
}

TEST_CASE("Queue::setMax() wakes a producer blocked in push()") {
    // Behavioural complement to the setMax source-text audit.  Source-text
    // checks can only prove the lock primitive and notify call exist in the
    // method body; they cannot prove that the actual runtime wakeup happens.
    // This test fills the queue to the cap, spawns a producer that blocks
    // in push(), confirms the producer really is parked in pushCond_.wait()
    // before changing the cap, then verifies that the producer completes —
    // proving that setMax() really does wake an already-blocked waiter.
    //
    // Two SUBCASEs cover both runtime contract paths:
    //   - "raising the cap to a larger value": setMax(10).  push() exits
    //     its wait when queue_.size() < max_ becomes true.
    //   - "disabling the cap with setMax(0)": setMax(0).  setMax(0) is
    //     the documented "no limit" special case, and push()'s wait
    //     predicate (max_ > 0 && size >= max_) becomes unconditionally
    //     false — a regression in the setMax(0) path (e.g. updating the
    //     cap without waking blocked producers) would leave the producer
    //     parked indefinitely against the old cap.
    //
    // Failure modes either SUBCASE catches that the source-text audit cannot:
    //   - dropping std::lock_guard<std::mutex>(mtx_) in setMax() reopens
    //     the check→wait lost-wakeup window: notify_all() can fire while
    //     no waiter is yet sleeping, leaving the producer asleep on the
    //     old cap until an unrelated pop()/stop().
    //   - dropping pushCond_.notify_all() leaves a producer that is
    //     already asleep on the old cap with no way to learn about the
    //     new value until an unrelated pop()/stop().
    //
    // Blocked-evidence handshake: `entered` is published *before* q.push(2),
    // so seeing entered=true alone does not prove the producer has reached
    // pushCond_.wait() — on a busy or instrumented runner, setMax could
    // fire before the producer even enters push(), and a lock-free
    // regression would then satisfy the new (raised) predicate on first
    // evaluation and complete the push without ever touching notify_all.
    // To rule that out, after entered=true the test runs a sustained-quiet
    // window that polls *both* `done` AND `q.size()`:
    //   - q.size() takes mtx_ on every call, so each successful poll proves
    //     mtx_ was reachable at that instant (the producer is not holding
    //     it across the window — predicate evaluation in push() takes
    //     microseconds).
    //   - q.size()==2 across the window proves the producer has not pushed
    //     past the wait predicate.
    //   - done==false across the window proves push() has not returned.
    // Across the window, the only states consistent with all three
    // observations are (a) the producer is parked in pushCond_.wait() with
    // mtx_ released, or (b) the producer's lambda has been continuously
    // descheduled between `entered.store(true)` and the push() entry for
    // the entire window.  (b) requires a 500 ms scheduler stall on two
    // consecutive simple statements, which is implausible on real CI even
    // under TSan/Valgrind; (a) is the contract this test is checking.
    //
    // Honest limitation: this is observational, not instrumented.  Truly
    // proving "producer is inside pushCond_.wait()" without false negatives
    // would require a hook inside Queue::push() to signal at the wait
    // entry point, which the public API does not expose.  Layer A's
    // structural audit catches the lock-free setMax regression
    // deterministically (no scheduling sensitivity); Layer B (this test)
    // catches the visible-runtime-breakage cases — dropped notify, dropped
    // lock that breaks the wakeup outright — with high but not perfect
    // probability.  The two layers are complementary.
    //
    // Cleanup ordering: the producer thread is stopped + joined BEFORE
    // any REQUIRE/CHECK assertion runs.  doctest's fatal assertions
    // unwind the stack on failure; if the std::thread is still joinable
    // at that point its destructor calls std::terminate().  Capturing
    // outcomes into locals first keeps the assertion phase cleanup-safe.

    // The active SUBCASE name is rendered by doctest in the failure
    // banner, so the scenario is already visible in test output without
    // having to thread a description string through CHECK_MESSAGE.
    uint32_t new_cap = 0;
    SUBCASE("raising the cap to a larger value") {
        new_cap = 10;
    }
    SUBCASE("disabling the cap with setMax(0)") {
        new_cap = 0;
    }

    rogue::Queue<int> q;
    q.setMax(2);

    // Fill queue to capacity (these calls must not block — queue is empty
    // before each push, then has 1 entry, then exactly hits the cap).
    q.push(0);
    q.push(1);

    std::atomic<bool> entered{false};
    std::atomic<bool> done{false};

    std::thread producer([&] {
        entered.store(true, std::memory_order_release);
        q.push(2);  // must block: queue at cap until setMax changes it.
        done.store(true, std::memory_order_release);
    });

    // Phase 1: wait for the producer's lambda to start.
    bool producer_started = false;
    {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!entered.load(std::memory_order_acquire) &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        producer_started = entered.load(std::memory_order_acquire);
    }

    // Phase 2: sustained-quiet-window check — for the full window we
    // require done==false (push() did not return) AND q.size() stays at
    // the initial cap (the producer did not make it past the wait
    // predicate).  Each q.size() call also takes mtx_ and releases it, so
    // a successful poll proves mtx_ was reachable at that instant — the
    // producer is not holding mtx_ across the window (predicate evaluation
    // in push() is microseconds, not 500 ms).  After per-thread started
    // evidence (Phase 1) plus 500 ms with no progress and no mtx_
    // contention, the only schedules consistent with these observations
    // are (a) the producer is parked in pushCond_.wait() — the contract
    // this test is checking — or (b) the producer's lambda has been
    // continuously descheduled between `entered.store(true)` and push()
    // entry for the entire window, which would require a 500 ms scheduler
    // stall on two consecutive simple statements.  Matches the
    // multi-producer SUBCASE below for the same reasons.
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

    // Phase 3: change the cap — must wake the producer.  Only fire setMax
    // once we have evidence the producer is parked in pushCond_.wait();
    // otherwise a lock-free regression would slip through because
    // push()'s first predicate evaluation already sees the new cap.
    if (producer_blocked) {
        q.setMax(new_cap);
    }

    // Phase 4: wait for completion with a generous timeout.
    bool producer_completed = false;
    {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!done.load(std::memory_order_acquire) &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        producer_completed = done.load(std::memory_order_acquire);
    }

    // Phase 5: cleanup BEFORE any fatal assertion fires.  If the producer
    // is still parked (broken setMax, or producer_blocked was false and
    // we never changed the cap), stop() drains the wait so join() returns.
    if (!producer_completed) {
        q.stop();
        // After stop(), Queue<T>::pop() returns a default-initialized T
        // and push() exits its wait without enqueueing; give the producer
        // a final chance to flip `done` before joining.
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!done.load(std::memory_order_acquire) &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    producer.join();

    // Phase 6: assertions run on captured state with the worker already
    // joined, so any fatal failure unwinds cleanly.
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
    // Behavioural complement to the source-text notify_all check.  Source
    // text proves the spelling `pushCond_.notify_all` appears in setMax();
    // this test proves the runtime contract — that *every* producer
    // blocked on the old cap re-evaluates against the new value.
    //
    // Failure mode this catches: a regression to pushCond_.notify_one()
    // wakes only one of N blocked producers.  Because push() itself only
    // issues popCond_.notify_all() on success (not pushCond_.notify_all),
    // the remaining N-1 producers stay parked until an unrelated
    // pop()/stop() — multiple-waiter starvation rather than the
    // single-waiter lost-wakeup the lock closes.
    //
    // Per-thread blocked evidence (not just an aggregate counter): a
    // shared `entered` counter combined with `done == 0` does not
    // guarantee every producer reached pushCond_.wait() before setMax
    // ran — a producer "in flight" between entered++ and the wait would
    // see the raised cap on its first predicate check and complete the
    // push without ever being notified, masking a notify_one() regression.
    // To rule that out, this test pairs per-thread `started[i]` flags
    // with a *sustained quiet window*: throughout the window we require
    //   - done == 0 (no producer's push() returned), AND
    //   - q.size() == initial cap (no producer made it past the wait
    //     predicate), AND
    //   - q.size() polling itself succeeds quickly on every iteration —
    //     each call takes mtx_, so a successful poll proves mtx_ was
    //     reachable at that instant (no producer is holding it across
    //     the window; predicate evaluation in push() takes microseconds).
    // After per-thread started flags AND 500 ms of all three signals
    // remaining stable, the only schedules consistent with the
    // observations are (a) every producer is parked in pushCond_.wait()
    // — the contract this test is checking — or (b) one or more
    // producers have been continuously descheduled between
    // started[i].store() and push() entry for the entire window.  (b)
    // would require sustained scheduler stalls on consecutive simple
    // statements, which is not seen in practice on CI even under
    // TSan/Valgrind; (a) is the contract.  A regressed notify_one()
    // then wakes one waiter; the remaining N-1 stay parked because
    // push() does not chain pushCond_ notifications.
    //
    // Honest limitation: this is observational, not instrumented.
    // Deterministically proving "every producer is inside
    // pushCond_.wait()" without false negatives would require a hook
    // inside Queue::push() to signal at the wait entry point, which the
    // public API does not expose.  Layer A's structural audit catches
    // the notify_one regression deterministically by pinning the literal
    // `pushCond_.notify_all` spelling in setMax(); Layer B (this test)
    // catches the visible-runtime-breakage cases with high but not
    // perfect probability.  The two layers are complementary.

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

    // Phase 1: wait for *every* producer's started[i] flag — per-thread
    // evidence that each lambda has begun, not just an aggregate count.
    bool all_started = false;
    {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (count_started() < N && std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        all_started = (count_started() == N);
    }

    // Phase 2: sustained-quiet-window check — for the full window
    // require done==0 (no producer completed push) AND q.size() stays
    // at the initial cap (no producer made it past the wait predicate).
    // This is the per-thread blocked evidence: per (1) above, every
    // producer's lambda is past started[i]; per this loop, no producer
    // pushed during the window; per the SUT structure, the only
    // remaining state for each producer is pushCond_.wait().  With
    // notify_one() each woken waiter would still satisfy the test, so
    // the per-producer "must be parked in pushCond_.wait()" invariant
    // is what makes the multi-waiter test discriminative.
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

    // Phase 3: raise cap to fit the queued entries (2) plus all blocked
    // producers (N).  All N must wake; with notify_one() only one would.
    if (all_blocked) {
        q.setMax(2 + N);
    }

    // Phase 4: wait for completion with a generous timeout.
    int completed = 0;
    {
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(4);
        while (done.load(std::memory_order_acquire) < N &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        completed = done.load(std::memory_order_acquire);
    }

    // Phase 5: cleanup BEFORE any fatal assertion fires.
    if (completed < N) {
        q.stop();
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (done.load(std::memory_order_acquire) < N &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    for (auto& p : producers) p.join();

    // Phase 6: assertions on captured state with workers joined.
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
    // Behavioural complement to the setThold source-text audit.  Source-text
    // checks can prove that setThold() touches busy_ and queue_.size() in
    // the same body, but they cannot prove that the recompute happens at
    // setThold() call time rather than (e.g.) being deferred to the next
    // push()/pop().  This test fills the queue, then calls setThold() with
    // values that straddle the current depth and asserts that busy() flips
    // accordingly *without* an intervening push()/pop()/reset().
    //
    // Purely deterministic — no threading, no scheduling sensitivity.

    rogue::Queue<int> q;
    q.push(0);
    q.push(1);
    q.push(2);
    REQUIRE(q.size() == 3u);

    // thold_ defaults to 0 — busy() must be false regardless of depth.
    CHECK_FALSE(q.busy());

    // Threshold strictly above current depth — busy() must remain false.
    q.setThold(10);
    CHECK_FALSE(q.busy());

    // Threshold at current depth — busy() must flip true *immediately*.
    // Without recomputing busy_ at setThold() time, busy() would keep
    // reporting the pre-setThold state until the next push()/pop()/reset().
    q.setThold(3);
    CHECK_MESSAGE(q.busy(),
                  "Queue::setThold() did not recompute busy_ at call time; "
                  "busy() still reports the pre-setThold state.  The "
                  "recompute must consult queue_.size() under mtx_ at the "
                  "moment the threshold changes, not on the next "
                  "push()/pop()/reset().");

    // Threshold below current depth — busy() must remain true.
    q.setThold(1);
    CHECK(q.busy());

    // Raise threshold above current depth — busy() must clear immediately.
    q.setThold(100);
    CHECK_FALSE(q.busy());

    // setThold(0) is the documented "no threshold" special case: busy()
    // must stay false regardless of queue depth.  At this point the queue
    // still holds 3 entries.  A regression that drops the (thold > 0)
    // guard and computes busy_ = (queue_.size() >= thold_) would compute
    // (3 >= 0) = true here while still passing every nonzero case above
    // — so this is the only step in the suite that pins the zero-threshold
    // contract.
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
