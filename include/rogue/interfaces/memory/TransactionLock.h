/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Transaction lock
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
#ifndef __ROGUE_INTERFACES_MEMORY_TRANSACTION_LOCK_H__
#define __ROGUE_INTERFACES_MEMORY_TRANSACTION_LOCK_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

namespace rogue {
namespace interfaces {
namespace memory {

class Transaction;

/**
 * @brief Scoped lock wrapper for a memory transaction.
 *
 * @details
 * Holds a lock on transaction data while client code accesses it. The lock prevents
 * transaction destruction while a slave updates data and completion state. Instances
 * are created via `Transaction::lock()`.
 */
class TransactionLock {
    std::shared_ptr<rogue::interfaces::memory::Transaction> tran_;
    bool locked_;

  public:
    /**
     * @brief Creates a transaction lock wrapper.
     *
     * @details
     * Parameter semantics are identical to the constructor; see `TransactionLock()`
     * for lock-wrapper behavior details.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param transaction Transaction to guard.
     * @return Shared pointer to the created lock object.
     */
    static std::shared_ptr<rogue::interfaces::memory::TransactionLock> create(
        std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

    /**
     * @brief Constructs a lock wrapper for the provided transaction.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * @param transaction Transaction to guard.
     */
    explicit TransactionLock(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

    /**
     * @brief Registers this type with Python bindings.
     */
    static void setup_python();

    /**
     * @brief Destroys the wrapper and releases any held lock.
     */
    ~TransactionLock();

    /**
     * @brief Locks the associated transaction when not already locked.
     *
     * @details Exposed as `lock()` in Python.
     */
    void lock();

    /**
     * @brief Unlocks the associated transaction when currently locked.
     *
     * @details Exposed as `unlock()` in Python.
     */
    void unlock();

    /**
     * @brief Python context-manager entry hook.
     *
     * @details
     * Exists to support Python `with` usage. Exposed as `__enter__()` in Python.
     */
    void enter();

    /**
     * @brief Python context-manager exit hook.
     *
     * @details
     * Exists to support Python `with` usage. Exposed as `__exit__()` in Python.
     */
    void exit(void*, void*, void*);
};

/**
 * @brief Shared pointer alias for `TransactionLock`.
 */
typedef std::shared_ptr<rogue::interfaces::memory::TransactionLock> TransactionLockPtr;

}  // namespace memory
}  // namespace interfaces
}  // namespace rogue

#endif
