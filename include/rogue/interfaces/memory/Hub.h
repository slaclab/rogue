/**
  * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * A memory interface hub. Accepts requests from multiple masters and forwards
 * them to a downstream slave. Address is updated along the way. Includes support
 * for modification callbacks.
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
#ifndef __ROGUE_INTERFACES_MEMORY_HUB_H__
#define __ROGUE_INTERFACES_MEMORY_HUB_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <string>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/memory/Slave.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {
namespace memory {

/**
 * @brief Memory interface Hub device.
 *
 * @details
 * The memory bus Hub serves as both a Slave and a Master for memory transactions. It
 * will accept a Transaction from an attached Master and pass it down to the next
 * level Slave or Hub device. It will apply its local offset address to the transaction
 * as it is passed down to the next level.
 *
 * A Hub can be sub-classed in either Python or C++ is order to further manipulate the
 * transaction data on the way down or convert the initial Transaction into multiple
 * transactions to the next level. This can be useful to hide complex windows memory
 * spaces or transactions that require multiplied steps be performed in hardware.
 *
 * If a non zero `min` and `max` transaction size are passed at creation this Hub will
 * behave as if it is a new root `Slave` memory device in the tree. This is useful in
 * cases where this `Hub` will master a paged address or other virtual address space.
 *
 * Access-size behavior is selected by the `min`/`max` constructor parameters:
 * - `min == 0` and `max == 0`: pass-through mode. Access-size identity/name queries
 *   are forwarded to the downstream interface.
 * - `min != 0` and `max != 0`: virtual-root mode. This hub advertises its own
 *   Slave-like identity and access limits (`min`/`max`) to upstream masters.
 * - Mixed values (`min == 0, max != 0` or `min != 0, max == 0`): also pass-through
 *   mode (virtual-root mode is not enabled).
 *
 * In other words, this hub behaves as a virtual root only when both `min` and `max`
 * are non-zero.
 *
 * A pyrogue.Device instance is the most typical Hub used in Rogue.
 */
class Hub : public Master, public Slave {
    // Offset address of hub
    uint64_t offset_;

    // Flag if this is a base slave
    bool root_;

    /**
     * @brief Logger for hub activity.
     */
    std::shared_ptr<rogue::Logging> log_;

  public:
    /**
     * @brief Creates a memory Hub.
     *
     * @details
     * Exposed to Python as `rogue.interfaces.memory.Hub()`.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     * Parameter semantics are identical to the constructor; see `Hub()` for
     * virtual-root behavior details.
     *
     * @param offset The offset of this Hub device.
     * @param min Minimum transaction size in virtual-root mode. Use `0` with `max=0`
     *            to disable virtual-root mode.
     * @param max Maximum transaction size in virtual-root mode. Use `0` with `min=0`
     *            to disable virtual-root mode.
     * @return Shared pointer to the created hub.
     */
    static std::shared_ptr<rogue::interfaces::memory::Hub> create(uint64_t offset, uint32_t min, uint32_t max);

    // Setup class for use in python
    static void setup_python();

    /**
     * @brief Constructs a Hub with optional virtual-root access constraints.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * Virtual-root mode is enabled only when both `min` and `max` are non-zero.
     * When both are zero, the hub behaves as a pass-through for access-limit queries.
     * Mixed values (only one non-zero) also behave as pass-through.
     *
     * @param offset The offset of this Hub device.
     * @param min Minimum transaction size in virtual-root mode. Use `0` with `max=0`
     *            to disable virtual-root mode.
     * @param max Maximum transaction size in virtual-root mode. Use `0` with `min=0`
     *            to disable virtual-root mode.
     */
    Hub(uint64_t offset, uint32_t min, uint32_t max);

    // Destroy the Hub
    ~Hub();

    /**
     * @brief Returns the local offset of this hub.
     *
     * @details
     * Exposed as `_getOffset()` to Python.
     *
     * @return 64-bit address offset
     */
    uint64_t getOffset();

    /**
     * @brief Returns the full address of this hub, including local offset.
     *
     * @details
     * Exposed as `_getAddress()` to Python.
     *
     * @return 64-bit address
     */
    uint64_t getAddress();

    /**
     * @brief Services `getSlaveId` request from an attached master.
     *
     * @details
     * By default the Hub forwards this request to the next level.
     * A hub may want to override this when mastering a virtual address space
     * such as a paged address map. Otherwise incorrect overlap errors may be
     * generated by the PyRogue Root.
     *
     * Not exposed to Python
     * @return 32-bit slave ID
     */
    uint32_t doSlaveId();

    /**
     * @brief Services `getSlaveName` request from an attached master.
     *
     * @details
     * By default the Hub forwards this request to the next level.
     * A hub may want to override this when mastering a virtual address space
     * such as a paged address map. Otherwise incorrect overlap errors may be
     * generated by the PyRogue Root.
     *
     * Not exposed to Python
     * @return slave name
     */
    std::string doSlaveName();

    /**
     * @brief Services `getMinAccess` request from an attached master.
     *
     * @details
     * This hub forwards the request to the next-level device.
     *
     * Not exposed to Python
     * @return Min transaction access size
     */
    uint32_t doMinAccess();

    /**
     * @brief Services `getMaxAccess` request from an attached master.
     *
     * @details
     * This hub forwards the request to the next-level device. A hub
     * sub-class is allowed to override this method.
     *
     * Not exposed to Python
     * @return Max transaction access size
     */
    uint32_t doMaxAccess();

    /**
     * @brief Services `getAddress` request from an attached master.
     *
     * @details
     * This hub forwards the request to the next-level device and applies
     * the local address offset. A Hub sub-class is allowed to override this method.
     *
     * Not exposed to Python
     * @return 64-bit address including this hub offset
     */
    uint64_t doAddress();

    /**
     * @brief Services a transaction request from an attached master.
     *
     * @details
     * This hub forwards the request to the next-level device and applies
     * the local address offset.
     *
     * It is possible for this method to be overridden in either a Python or C++
     * subclass. Examples of sub-classing a Hub are included elsewhere in this
     * document.
     *
     * Exposed to Python as `_doTransaction()`.
     * @param transaction Transaction pointer as TransactionPtr.
     */
    virtual void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);
};

/** Alias for using shared pointer as HubPtr */
typedef std::shared_ptr<rogue::interfaces::memory::Hub> HubPtr;

#ifndef NO_PYTHON

/**
 * @brief Internal Boost.Python wrapper for `rogue::interfaces::memory::Hub`.
 * Enables Python subclasses to override virtual transaction handling.
 *
 *  This wrapper is an internal binding adapter and not a primary C++ API surface.
 *  It is registered by `setup_python()` under the base class name.
 */
class HubWrap : public rogue::interfaces::memory::Hub, public boost::python::wrapper<rogue::interfaces::memory::Hub> {
  public:
    /**
     * @brief Constructs a hub wrapper instance.
     * @param offset Local address offset applied by this hub.
     * @param min Minimum transaction size for virtual-root mode.
     * @param max Maximum transaction size for virtual-root mode.
     */
    HubWrap(uint64_t offset, uint32_t min, uint32_t max);

    /**
     * @brief Services a transaction request from an attached master.
     *
     * @details
     * Invokes the Python override when provided.
     *
     * @param transaction Transaction object to process.
     */
    void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);

    /**
     * @brief Calls the base-class `doTransaction()` implementation.
     *
     * @details
     * Used as the fallback when no Python override is present.
     *
     * @param transaction Transaction object to process.
     */
    void defDoTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);
};

// Convienence
typedef std::shared_ptr<rogue::interfaces::memory::HubWrap> HubWrapPtr;
#endif

}  // namespace memory
}  // namespace interfaces
}  // namespace rogue

#endif
