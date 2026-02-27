/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * A memory space emulator. Allows user to test a Rogue tree without real hardware.
 * This block will auto allocate memory as needed.
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
#ifndef __ROGUE_INTERFACES_MEMORY_EMULATOR_H__
#define __ROGUE_INTERFACES_MEMORY_EMULATOR_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>
#include <vector>

#include "rogue/interfaces/memory/Slave.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

#define EMULATE_MAP_TYPE std::map<uint64_t, uint8_t*>

namespace rogue {
namespace interfaces {
namespace memory {

/**
 * @brief Memory interface emulator device.
 *
 * @details
 * Responds to memory read and write transactions and allocates backing memory on demand.
 * This is primarily used for testing Rogue memory trees without hardware.
 */
class Emulate : public Slave {
    // Map to store 4K address space chunks
    EMULATE_MAP_TYPE memMap_;

    // Lock
    std::mutex mtx_;

    // Total allocated memory
    uint32_t totAlloc_;
    uint32_t totSize_;

    /**
     * @brief Logger for emulator activity.
     */
    std::shared_ptr<rogue::Logging> log_;

  public:
    /**
     * @brief Creates an emulator device.
     *
     * @details
     * Exposed to Python as `rogue.interfaces.memory.Emulate()`.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param min Minimum transaction size in bytes, or `0` if not a virtual root.
     * @param max Maximum transaction size in bytes, or `0` if not a virtual root.
     * @return Shared pointer to the created emulator.
     */
    static std::shared_ptr<rogue::interfaces::memory::Emulate> create(uint32_t min, uint32_t max);

    /**
     * @brief Registers this type with Python bindings.
     */
    static void setup_python();

    /**
     * @brief Constructs an emulator device.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * @param min Minimum transaction size in bytes, or `0` if not a virtual root.
     * @param max Maximum transaction size in bytes, or `0` if not a virtual root.
     */
    Emulate(uint32_t min, uint32_t max);

    /**
     * @brief Destroys the emulator device.
     */
    ~Emulate();

    /**
     * @brief Handles an incoming memory transaction.
     *
     * @param transaction Transaction to execute against emulated memory.
     */
    void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> transaction);
};

/**
 * @brief Shared pointer alias for `Emulate`.
 */
typedef std::shared_ptr<rogue::interfaces::memory::Emulate> EmulatePtr;
}  // namespace memory
}  // namespace interfaces
}  // namespace rogue

#endif
