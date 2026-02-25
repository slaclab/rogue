/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory slave interface.
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
#ifndef __ROGUE_INTERFACES_MEMORY_SLAVE_H__
#define __ROGUE_INTERFACES_MEMORY_SLAVE_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <map>
#include <memory>
#include <string>
#include <vector>

#include "rogue/EnableSharedFromThis.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/memory/Transaction.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {
namespace memory {

class Master;
class Transaction;

/**
 * @brief Memory slave device.
 *
 * @details
 * The memory Slave device accepts and services transactions from one or more Master devices.
 * The Slave device is normally sub-classed in either C++ or Python to provide an interfaces
 * to hardware or the next level memory transaction protocol, such as SrpV0 or SrpV3.
 * Examples of Slave sub-class implementations are included elsewhere in this document.
 *
 * The Slave object provides mechanisms for tracking current transactions.
 */
class Slave : public rogue::EnableSharedFromThis<rogue::interfaces::memory::Slave> {
    // Class instance counter
    static uint32_t classIdx_;

    // Class instance lock
    static std::mutex classMtx_;

    // Unique slave ID
    uint32_t id_;

    // Alias for map
    typedef std::map<uint32_t, std::shared_ptr<rogue::interfaces::memory::Transaction> > TransactionMap;

    // Transaction map
    TransactionMap tranMap_;

    // Slave lock
    std::mutex slaveMtx_;

    // Min access
    uint32_t min_;

    // Max access
    uint32_t max_;

    // Slave Name
    std::string name_;

  public:
    /**
     * @brief Creates a memory slave.
     *
     * @details
     * Exposed as `rogue.interfaces.memory.Slave()` to Python.
     *
     * `min` and `max` define the default access-size contract (in bytes) reported
     * by `doMinAccess()` and `doMaxAccess()`. The base `Slave` class stores and
     * returns these values as provided; higher-level classes may layer additional
     * semantics on top of them.
     *
     * @param min Minimum transaction size this slave can accept, in bytes.
     * @param max Maximum transaction size this slave can accept, in bytes.
     * @return Shared pointer to the created slave.
     */
    static std::shared_ptr<rogue::interfaces::memory::Slave> create(uint32_t min, uint32_t max);

    /**
     * @brief Registers this type with Python bindings.
     */
    static void setup_python();

    /**
     * @brief Constructs a memory slave.
     *
     * @details
     * `min` and `max` are stored as the local access-size contract and returned by
     * default `doMinAccess()`/`doMaxAccess()` implementations.
     *
     * @param min Minimum transaction size this slave can accept, in bytes.
     * @param max Maximum transaction size this slave can accept, in bytes.
     */
    Slave(uint32_t min, uint32_t max);

    /**
     * @brief Destroys the memory slave instance.
     */
    virtual ~Slave();

    /**
     * @brief Stops the memory slave interface.
     *
     * @details
     * Base implementation is a no-op. Subclasses may override to stop worker
     * threads or transport links.
     */
    virtual void stop();

    /**
     * @brief Adds a transaction to the internal tracking map.
     *
     * @details
     * This method is called by the sub-class to add a transaction into the local
     * tracking map for later retrieval. This is used when the transaction will be
     * completed later as the result of protocol data being returned to the Slave.
     *
     * Exposed to Python as `_addTransaction()`.
     *
     * @param transaction Pointer to transaction as TransactionPtr.
     */
    void addTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

    /**
     * @brief Gets a transaction from the internal tracking map.
     *
     * @details
     * This method is called by the sub-class to retrieve an existing transaction
     * using the unique transaction ID. If the transaction exists in the list the
     * pointer to that transaction will be returned. If not a NULL pointer will be
     * returned. When getTransaction() is called the map will also be checked for
     * stale transactions which will be removed from the map.
     *
     * Exposed to Python as `_getTransaction()`.
     *
     * @param index ID of transaction to lookup.
     * @return Pointer to transaction as TransactionPtr or NULL if not found.
     */
    std::shared_ptr<rogue::interfaces::memory::Transaction> getTransaction(uint32_t index);

    /**
     * @brief Returns configured minimum transaction size.
     *
     * @details Not exposed to Python.
     *
     * @return Minimum transaction size in bytes.
     */
    uint32_t min();

    /**
     * @brief Returns configured maximum transaction size.
     *
     * @details Not exposed to Python.
     *
     * @return Maximum transaction size in bytes.
     */
    uint32_t max();

    /**
     * @brief Returns unique slave ID.
     *
     * @details Not exposed to Python.
     *
     * @return Unique slave ID.
     */
    uint32_t id();

    /**
     * @brief Sets slave name.
     *
     * @details Exposed to Python as `setName`.
     *
     * @param name New slave name string.
     */
    void setName(std::string name);

    /**
     * @brief Returns slave name.
     *
     * @details Not exposed to Python.
     *
     * @return Slave name.
     */
    std::string name();

    /**
     * @brief Services `SlaveId` request from a master.
     *
     * @details
     * Called by memory `Master`. Subclasses may override.
     * Base implementation returns local slave ID.
     * Not exposed to Python.
     *
     * @return Unique slave ID.
     */
    virtual uint32_t doSlaveId();

    /**
     * @brief Services `SlaveName` request from a master.
     *
     * @details
     * Called by memory `Master`. Subclasses may override.
     * Base implementation returns local slave name.
     * Not exposed to Python.
     *
     * @return Slave name.
     */
    virtual std::string doSlaveName();

    /**
     * @brief Services `getMinAccess` request from an attached master.
     *
     * @details
     * Base implementation returns local `min()` value. Subclasses may override.
     * Exposed as `_doMinAccess()` to Python.
     *
     * @return Minimum transaction access size in bytes.
     */
    virtual uint32_t doMinAccess();

    /**
     * @brief Services `getMaxAccess` request from an attached master.
     *
     * @details
     * Base implementation returns local `max()` value. Subclasses may override.
     * Exposed as `_doMaxAccess()` to Python.
     *
     * @return Maximum transaction access size in bytes.
     */
    virtual uint32_t doMaxAccess();

    /**
     * @brief Services `getAddress` request from an attached master.
     *
     * @details
     * Base implementation returns `0`. Subclasses may override to contribute an
     * address offset.
     * Exposed as `_doAddress()` to Python.
     *
     * @return Address offset in bytes.
     */
    virtual uint64_t doAddress();

    /**
     * @brief Services a transaction request from an attached master.
     *
     * It is possible for this method to be overridden in either a Python or C++
     * subclass. Examples of sub-classing a Slave is included elsewhere in this
     * document.
     *
     * @details
     * Base implementation reports an unsupported-transaction error.
     * Exposed to Python as `_doTransaction()`.
     *
     * @param transaction Transaction pointer as TransactionPtr.
     */
    virtual void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

#ifndef NO_PYTHON

    /**
     * @brief Supports `<<` operator usage from Python.
     *
     * @param p Python object expected to provide a memory `Master`.
     */
    void lshiftPy(boost::python::object p);

#endif

    /**
     * @brief Connects this slave to a master via chaining operator.
     *
     * @details Equivalent to `other->setSlave(this)` semantics.
     *
     * @param other Memory master to connect.
     * @return Reference to the passed master pointer.
     */
    std::shared_ptr<rogue::interfaces::memory::Master>& operator<<(
        std::shared_ptr<rogue::interfaces::memory::Master>& other);
};

/** @brief Shared pointer alias for `Slave`. */
typedef std::shared_ptr<rogue::interfaces::memory::Slave> SlavePtr;

#ifndef NO_PYTHON

// Memory slave class, wrapper to enable python overload of virtual methods
class SlaveWrap : public rogue::interfaces::memory::Slave,
                  public boost::python::wrapper<rogue::interfaces::memory::Slave> {
  public:
    /**
     * @brief Constructs a memory-slave wrapper instance.
     *
     * @param min Minimum transaction size this slave can accept, in bytes.
     * @param max Maximum transaction size this slave can accept, in bytes.
     */
    SlaveWrap(uint32_t min, uint32_t max);

    /**
     * @brief Returns minimum transaction access size.
     *
     * @details Invokes the Python override when provided.
     *
     * @return Minimum transaction access size in bytes.
     */
    uint32_t doMinAccess();

    /**
     * @brief Calls the base-class `doMinAccess()` implementation.
     *
     * @details Used as the fallback when no Python override is present.
     *
     * @return Minimum transaction access size in bytes.
     */
    uint32_t defDoMinAccess();

    /**
     * @brief Returns maximum transaction access size.
     *
     * @details Invokes the Python override when provided.
     *
     * @return Maximum transaction access size in bytes.
     */
    uint32_t doMaxAccess();

    /**
     * @brief Calls the base-class `doMaxAccess()` implementation.
     *
     * @details Used as the fallback when no Python override is present.
     *
     * @return Maximum transaction access size in bytes.
     */
    uint32_t defDoMaxAccess();

    /**
     * @brief Returns base address contribution for this slave.
     *
     * @details Invokes the Python override when provided.
     *
     * @return Address offset in bytes.
     */
    uint64_t doAddress();

    /**
     * @brief Calls the base-class `doAddress()` implementation.
     *
     * @details Used as the fallback when no Python override is present.
     *
     * @return Address offset in bytes.
     */
    uint64_t defDoAddress();

    /**
     * @brief Services a transaction request from an attached master.
     *
     * @details Invokes the Python override when provided.
     *
     * @param transaction Transaction object to process.
     */
    void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

    /**
     * @brief Calls the base-class `doTransaction()` implementation.
     *
     * @details Used as the fallback when no Python override is present.
     *
     * @param transaction Transaction object to process.
     */
    void defDoTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);
};

typedef std::shared_ptr<rogue::interfaces::memory::SlaveWrap> SlaveWrapPtr;
#endif

}  // namespace memory
}  // namespace interfaces
}  // namespace rogue

#endif
