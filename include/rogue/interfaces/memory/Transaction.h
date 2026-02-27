/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Transaction
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
#ifndef __ROGUE_INTERFACES_MEMORY_TRANSACTION_H__
#define __ROGUE_INTERFACES_MEMORY_TRANSACTION_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <condition_variable>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>

#include "rogue/EnableSharedFromThis.h"
#include "rogue/Logging.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {
namespace memory {

class TransactionLock;
class Transaction;
class Master;
class Hub;

//         using TransactionIDVec = std::vector<uint32_t>;
//         using TransactionQueue = std::queue<std::shared_ptr<rogue::interfaces::memory::Transaction>>;
using TransactionMap = std::map<uint32_t, std::shared_ptr<rogue::interfaces::memory::Transaction>>;

/**
 * @brief Memory transaction container passed between master and slave.
 *
 * @details
 * Encapsulates a single memory operation request and completion state while it moves
 * between `Master` and `Slave` layers.
 *
 * Lifecycle and ownership:
 * - Instances are created internally by `Master`; callers do not construct them directly.
 * - A transaction is identified by a unique 32-bit ID.
 * - Data is accessed through an internal byte iterator and guarded by `TransactionLock`.
 * - Completion is signaled via `done()` or `error*()` and may be observed by wait logic.
 *
 * Timeout and completion behavior:
 * - A per-transaction timeout is captured at creation and used by wait/refresh logic.
 * - Transactions may expire when timeout is reached before completion.
 * - Timeout refresh can propagate from parent/peer activity to avoid premature expiration.
 *
 * Subtransaction behavior:
 * - A transaction can be split into child subtransactions.
 * - Parent tracks children in `subTranMap_` and completes only after all children complete
 *   (or propagates child error to the parent).
 *
 * Python integration:
 * - Python buffer-backed transactions are supported when Python APIs are used.
 * - Accessors such as `id()`, `address()`, `size()`, `type()`, and `expired()` are
 *   exposed to Python bindings.
 */
class Transaction : public rogue::EnableSharedFromThis<rogue::interfaces::memory::Transaction> {
    friend class TransactionLock;
    friend class Master;
    friend class Hub;

  public:
    /** @brief Iterator alias for transaction byte access. */
    typedef uint8_t* iterator;

  private:
    // Class instance counter
    static uint32_t classIdx_;

    // Class instance lock
    static std::mutex classMtx_;

    // Conditional
    std::condition_variable cond_;

  protected:
    // Transaction timeout
    struct timeval timeout_;

    // Transaction end time
    struct timeval endTime_;

    // Transaction start time
    struct timeval startTime_;

    // Transaction warn time
    struct timeval warnTime_;

#ifndef NO_PYTHON
    // Transaction python buffer
    Py_buffer pyBuf_;
#endif

    // Python buffer is valid
    bool pyValid_;

    // Iterator (mapped to uint8_t * for now)
    iterator iter_;

    // Transaction address
    uint64_t address_;

    // Transaction size
    uint32_t size_;

    // Transaction type
    uint32_t type_;

    // Transaction error
    std::string error_;

    // Transaction id
    uint32_t id_;

    // Done state
    bool done_;

    // Transaction lock
    std::mutex lock_;

    // Sub-transactions vector
    TransactionMap subTranMap_;

    // Done creating subtransactions for this transaction
    bool doneCreatingSubTransactions_;

    // Identify if it's a parent or a sub transaction
    bool isSubTransaction_;

    /** Logger for transaction activity. */
    std::shared_ptr<rogue::Logging> log_;

    // Weak pointer to parent transaction, where applicable
    std::weak_ptr<rogue::interfaces::memory::Transaction> parentTransaction_;

    /**
     * @brief Creates a transaction container.
     *
     * @details
     * Private/internal factory used by `Master` to allocate transaction
     * instances with shared ownership and lifecycle tracking.
     * Parameter semantics are identical to the constructor; see `Transaction()`.
     * This static factory is the preferred construction path when shared ownership
     * is required across asynchronous request/response paths.
     */
    static std::shared_ptr<rogue::interfaces::memory::Transaction> create(struct timeval timeout);

    // Wait for the transaction to complete, called by Master
    std::string wait();

  public:
    // Setup class for use in python
    static void setup_python();

    /**
     * @brief Constructs a transaction container.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` for normal transaction lifecycle management.
     * Do not call this constructor directly in normal use; transactions are
     * expected to be created by `Master` through the internal `create()` path.
     * That path ensures consistent ownership and integration with transaction
     * request/wait bookkeeping.
     *
     * @param timeout Initial timeout value copied into this transaction.
     */
    explicit Transaction(struct timeval timeout);

    // Destroy the Transaction.
    ~Transaction();

    /**
     * @brief Locks the transaction and returns a lock wrapper.
     *
     * @details Exposed as `lock()` in Python.
     *
     * @return Transaction lock pointer.
     */
    std::shared_ptr<rogue::interfaces::memory::TransactionLock> lock();

    /**
     * @brief Returns whether this transaction has expired.
     *
     * @details
     * Expiration is set by `Master` when timeout occurs and no further waiting is
     * performed. The lock must be held before checking expiration state.
     * Exposed as `expired()` in Python.
     *
     * @return `true` if transaction is expired; otherwise `false`.
     */
    bool expired();

    /**
     * @brief Returns the transaction ID.
     *
     * @details Exposed as `id()` in Python.
     *
     * @return 32-bit transaction ID.
     */
    uint32_t id();

    /**
     * @brief Returns the transaction address.
     *
     * @details Exposed as `address()` in Python.
     *
     * @return 64-bit transaction address.
     */
    uint64_t address();

    /**
     * @brief Returns the transaction size.
     *
     * @details Exposed as `size()` in Python.
     *
     * @return 32-bit transaction size in bytes.
     */
    uint32_t size();

    /**
     * @brief Returns the transaction type constant.
     *
     * @details
     * Type values are defined in `rogue/interfaces/memory/Constants.h`, including:
     * - `rogue::interfaces::memory::Read`
     * - `rogue::interfaces::memory::Write`
     * - `rogue::interfaces::memory::Post`
     * - `rogue::interfaces::memory::Verify`
     *
     * Exposed as `type()` in Python.
     *
     * @return 32-bit transaction type.
     */
    uint32_t type();

    /**
     * @brief Creates a subtransaction linked to this parent transaction.
     *
     * @return Pointer to the newly created subtransaction.
     */
    std::shared_ptr<rogue::interfaces::memory::Transaction> createSubTransaction();

    /** @brief Marks subtransaction creation as complete for this transaction. */
    void doneSubTransactions();

    /**
     * @brief Refreshes the transaction timer.
     *
     * @details
     * Timer is refreshed when `reference` is null or when this transaction start time
     * is later than the reference transaction start time. Not exposed to Python.
     *
     * @param reference Reference transaction.
     */
    void refreshTimer(std::shared_ptr<rogue::interfaces::memory::Transaction> reference);

    /**
     * @brief Marks transaction completion without error.
     *
     * @details
     * The transaction lock must be held before calling this method.
     * Exposed as `done()` in Python.
     */
    void done();

    /**
     * @brief Marks transaction completion with an error string (Python interface).
     *
     * @details
     * The transaction lock must be held before calling this method.
     * Exposed as `error()` in Python.
     *
     * @param error Transaction error message.
     */
    void errorStr(std::string error);

    /**
     * @brief Marks transaction completion with a formatted C-string error.
     *
     * @details The transaction lock must be held before calling this method.
     */
    void error(const char* fmt, ...);

    /**
     * @brief Returns iterator to the beginning of transaction data.
     *
     * @details
     * Not exposed to Python. Lock must be held before calling this method and while
     * updating transaction data.
     *
     * @return Data iterator.
     */
    uint8_t* begin();

    /**
     * @brief Returns iterator to the end of transaction data.
     *
     * @details
     * Not exposed to Python. Lock must be held before calling this method and while
     * updating transaction data.
     *
     * @return Data iterator.
     */
    uint8_t* end();

#ifndef NO_PYTHON

    /**
     * @brief Copies transaction data into a Python byte-array-like object.
     *
     * @details
     * Exposed to Python as `getData()`. The copy size is defined by the provided
     * destination buffer size.
     *
     * @param p Python byte-array-like destination object.
     * @param offset Offset for transaction data access.
     */
    void getData(boost::python::object p, uint32_t offset);

    /**
     * @brief Copies data from a Python byte-array-like object into the transaction.
     *
     * @details
     * Exposed to Python as `setData()`. The copy size is defined by the provided
     * source buffer size.
     *
     * @param p Python byte-array-like source object.
     * @param offset Offset for transaction data access.
     */
    void setData(boost::python::object p, uint32_t offset);
#endif
};

/** @brief Shared pointer alias for `Transaction`. */
typedef std::shared_ptr<rogue::interfaces::memory::Transaction> TransactionPtr;

}  // namespace memory
}  // namespace interfaces
}  // namespace rogue

#endif
