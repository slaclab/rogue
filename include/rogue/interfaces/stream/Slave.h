/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface slave
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
#ifndef __ROGUE_INTERFACES_STREAM_SLAVE_H__
#define __ROGUE_INTERFACES_STREAM_SLAVE_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <string>
#include <thread>

#include "rogue/EnableSharedFromThis.h"
#include "rogue/Logging.h"
#include "rogue/interfaces/stream/Pool.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {
namespace stream {

class Frame;
class Buffer;
class Master;

/**
 * @brief Stream slave endpoint and default frame pool.
 *
 * @details
 * A `Slave` receives frames from upstream masters via `acceptFrame()` and also
 * implements `Pool`, so it can service frame-allocation requests in the same
 * stream path. A single slave can be attached to multiple masters.
 *
 * `Slave` is not abstract (no pure virtual methods), but it is intended to be
 * subclassed for most real applications (protocol endpoints, transforms, sinks,
 * file/network bridges).
 *
 * Subclass contract in practice:
 * - Primary override point: `acceptFrame()`. Implement per-frame ingress logic
 *   here (decode, transform, queue, forward, or consume).
 * - Optional lifecycle override: `stop()`. Override when the subclass owns
 *   worker threads, timers, sockets, or device resources needing clean shutdown.
 * - Optional allocation overrides (from `Pool`): `acceptReq()` and `retBuffer()`
 *   when custom memory allocation/recycling is needed (for example DMA-backed
 *   buffers).
 *
 * Base-class behavior notes:
 * - Base `acceptFrame()` increments frame/byte counters and can emit debug
 *   logging (`setDebug()`), while taking a frame lock during inspection.
 * - If a subclass overrides `acceptFrame()` and still wants those counters/debug
 *   semantics, it should explicitly call `Slave::acceptFrame(frame)` or provide
 *   equivalent logic.
 */
class Slave : public rogue::interfaces::stream::Pool,
              public rogue::EnableSharedFromThis<rogue::interfaces::stream::Slave> {
    // Mutex
    std::mutex mtx_;

    // Debug control
    uint32_t debug_;
    std::shared_ptr<rogue::Logging> log_;

    // Counters
    uint64_t frameCount_;
    uint64_t frameBytes_;

  public:
    /**
     * @brief Creates a new stream slave.
     *
     * @details Exposed as `rogue.interfaces.stream.Slave()` in Python.
     *
     * @return Shared pointer to a newly created slave.
     */
    static std::shared_ptr<rogue::interfaces::stream::Slave> create();

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /** @brief Constructs a stream slave. */
    Slave();

    /** @brief Destroys the stream slave. */
    virtual ~Slave();

    /**
     * @brief Shuts down threads associated with this object.
     *
     * @details
     * Called during shutdown to stop activity and allow clean process exit.
     * Subclasses should override when they own worker threads or timers.
     *
     * Exposed as `stop()` in Python.
     */
    virtual void stop();

    /**
     * @brief Sets debug message verbosity and logger name.
     *
     * @details
     * This method enables debug messages when using the base Slave class
     * attached as a primary or secondary Slave on a Master. Typically used
     * when attaching a base Slave object for debug purposes.
     *
     * Exposed as `setDebug()` in Python.
     *
     * @param debug Maximum number of bytes to print in debug message.
     * @param name Name included in debug messages.
     */
    void setDebug(uint32_t debug, std::string name);

    /**
     * @brief Accepts a frame from a master.
     *
     * @details
     * This method is called by the Master object to which this Slave is attached when
     * passing a Frame. By default this method will print debug information if enabled
     * and is typically re-implemented by a Slave sub-class. This is the primary
     * subclass extension point for implementing stream processing behavior.
     *
     * Base implementation behavior:
     * - Increments `getFrameCount()` / `getByteCount()` counters.
     * - Acquires a frame lock and optionally logs data bytes per `setDebug()`.
     *
     * Re-implemented as `_acceptFrame()` in Python subclasses.
     *
     * @param frame Frame pointer (FramePtr).
     */
    virtual void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Returns frame counter.
     *
     * @details
     * Returns the total frames received. Only valid if acceptFrame is not re-implemented
     * as a sub-class. Typically used when attaching a base Slave object for debug purposes.
     *
     * Exposed as `getFrameCount()` in Python.
     *
     * @return Total number of Frame objects received.
     */
    uint64_t getFrameCount();

    /**
     * @brief Returns byte counter.
     *
     * @details
     * Returns the total bytes received. Only valid if acceptFrame is not re-implemented
     * as a sub-class. Typically used when attaching a base Slave object for debug purposes.
     *
     * Exposed as `getByteCount()` in Python.
     *
     * @return Total number of bytes received.
     */
    uint64_t getByteCount();

    /**
     * @brief Ensures frame is backed by a single buffer.
     *
     * @details
     * This method makes sure the passed frame is composed of a single buffer.
     * If the `reqEn` flag is true and the passed frame is not single-buffer, a
     * new frame can be requested and data copied into it, updating the passed
     * frame pointer. A frame lock must be held when this method is called.
     *
     * Not exposed to Python.
     *
     * @param frame Reference to frame pointer (FramePtr).
     * @param reqEn Flag to determine if a new frame should be requested.
     * @return `true` if frame is single-buffer after processing.
     */
    bool ensureSingleBuffer(std::shared_ptr<rogue::interfaces::stream::Frame>& frame, bool reqEn);

    /**
     * @brief Services a local frame allocation request through this object's pool interface.
     *
     * @details
     * This bypasses upstream links and allocates from the local Pool implementation.
     *
     * @param size Minimum required frame payload size in bytes.
     * @param zeroCopyEn True to allow zero-copy buffer use when supported.
     * @return Newly allocated frame pointer.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> reqLocalFrame(uint32_t size, bool zeroCopyEn);

#ifndef NO_PYTHON

    /**
     * @brief Supports `<<` operator usage from Python.
     * @param p Python object expected to resolve to a stream `Master`.
     * @return Original Python object for chaining semantics.
     */
    boost::python::object lshiftPy(boost::python::object p);

#endif

    /**
     * @brief Connects this slave to a master via stream chaining operator.
     * @param other Upstream master to attach.
     * @return Reference to `other` for chaining.
     */
    std::shared_ptr<rogue::interfaces::stream::Master>& operator<<(
        std::shared_ptr<rogue::interfaces::stream::Master>& other);
};

/** @brief Shared pointer alias for `Slave`. */
typedef std::shared_ptr<rogue::interfaces::stream::Slave> SlavePtr;

#ifndef NO_PYTHON

/**
 * @brief Internal Boost.Python wrapper for `rogue::interfaces::stream::Slave`.
 * Enables Python subclasses to override virtual methods.
 *
 *  This wrapper is an internal binding adapter and not a primary C++ API surface.
 *  It is registered by `setup_python()` under the base class name.
 */
class SlaveWrap : public rogue::interfaces::stream::Slave,
                  public boost::python::wrapper<rogue::interfaces::stream::Slave> {
  public:
    /**
     * @brief Accepts a frame from an upstream master.
     *
     * @details
     * Invokes the Python override when provided.
     *
     * @param frame Frame received from the stream path.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Calls the base-class `acceptFrame()` implementation.
     *
     * @details
     * Used as the fallback when no Python override is present.
     *
     * @param frame Frame received from the stream path.
     */
    void defAcceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);
};

typedef std::shared_ptr<rogue::interfaces::stream::SlaveWrap> SlaveWrapPtr;
#endif

}  // namespace stream
}  // namespace interfaces
}  // namespace rogue
#endif
