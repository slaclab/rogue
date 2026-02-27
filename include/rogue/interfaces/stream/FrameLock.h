/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Memory Frame lock
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
#ifndef __ROGUE_INTERFACES_MEMORY_FRAME_LOCK_H__
#define __ROGUE_INTERFACES_MEMORY_FRAME_LOCK_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

namespace rogue {
namespace interfaces {
namespace stream {

class Frame;

/**
 * @brief Scoped lock wrapper for stream frames.
 *
 * @details
 * Holds a lock while frame data is accessed. This allows multiple stream slaves to
 * read/update safely while ensuring only one updater at a time. Locks are released
 * on destruction. Instances are created via `Frame::lock()`.
 */
class FrameLock {
    std::shared_ptr<rogue::interfaces::stream::Frame> frame_;
    bool locked_;

  public:
    /**
     * @brief Creates a frame lock wrapper.
     *
     * @details Intended for internal use by `Frame`.
     * Parameter semantics are identical to the constructor; see `FrameLock()`
     * for lock-wrapper behavior details.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @param frame Frame to lock.
     * @return Shared pointer to the created lock object.
     */
    static std::shared_ptr<rogue::interfaces::stream::FrameLock> create(
        std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Constructs a lock wrapper for the provided frame.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     *
     * @param frame Frame to lock.
     */
    explicit FrameLock(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /** @brief Destroys the wrapper and releases any held lock. */
    ~FrameLock();

    /**
     * @brief Locks the associated frame when not already locked.
     *
     * @details Exposed as `lock()` in Python.
     */
    void lock();

    /**
     * @brief Unlocks the associated frame when currently locked.
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

/** @brief Shared pointer alias for `FrameLock`. */
typedef std::shared_ptr<rogue::interfaces::stream::FrameLock> FrameLockPtr;

}  // namespace stream
}  // namespace interfaces
}  // namespace rogue

#endif
