/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Stream interface master
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
#ifndef __ROGUE_INTERFACES_STREAM_MASTER_H__
#define __ROGUE_INTERFACES_STREAM_MASTER_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <cstdio>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "rogue/EnableSharedFromThis.h"

#ifndef NO_PYTHON
    #include <boost/python.hpp>
#endif

namespace rogue {
namespace interfaces {
namespace stream {

class Slave;
class Frame;

/**
 * @brief Stream master endpoint.
 *
 * @details
 * Source object for sending frames to one or more stream slaves. The first
 * attached slave is used to allocate new frames and is the last to receive
 * sent frames.
 *
 * `Master` is not an abstract class (no pure virtual methods), but it is
 * commonly used as a base for protocol/source implementations.
 *
 * Subclass expectations in practice:
 * - No `Master` method is required to be overridden.
 * - Most subclasses keep `addSlave()`, `reqFrame()`, and `sendFrame()` as-is
 *   and call `reqFrame()`/`sendFrame()` from their own public APIs or worker
 *   threads (for example protocol transmit paths and file readers).
 * - `stop()` is the primary `Master` method intended for override when the
 *   subclass owns worker threads, timers, sockets, or device handles.
 * - For transform/bridge classes that are both source and sink, ingress logic
 *   is usually implemented by also inheriting `Slave` and overriding
 *   `Slave::acceptFrame()`, while egress uses this `Master` interface.
 */
class Master : public rogue::EnableSharedFromThis<rogue::interfaces::stream::Master> {
    // Vector of slaves
    std::vector<std::shared_ptr<rogue::interfaces::stream::Slave> > slaves_;

    // Slave mutex
    std::mutex slaveMtx_;

    // Default slave if not connected
    std::shared_ptr<rogue::interfaces::stream::Slave> defSlave_;

  public:
    /**
     * @brief Creates a stream master.
     *
     * @details
     * Exposed as `rogue.interfaces.stream.Master()` in Python.
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created master.
     */
    static std::shared_ptr<rogue::interfaces::stream::Master> create();

    /** @brief Registers this type with Python bindings. */
    static void setup_python();

    /**
     * @brief Constructs a stream master.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    Master();

    /** @brief Destroys the stream master. */
    virtual ~Master();

    /**
     * @brief Returns the number of attached slaves.
     *
     * @details Exposed as `_slaveCount()` in Python.
     *
     * @return Number of attached slaves.
     */
    uint32_t slaveCount();

    /**
     * @brief Attaches a downstream slave.
     *
     * @details
     * Multiple slaves are supported. The first attached slave is used for frame
     * allocation and receives frames last during send.
     * Exposed as `_addSlave()` in Python.
     *
     * @param slave Stream slave pointer.
     */
    void addSlave(std::shared_ptr<rogue::interfaces::stream::Slave> slave);

    /**
     * @brief Requests allocation of a new frame from the primary slave.
     *
     * @details
     * Creates an empty frame with at least the requested payload capacity.
     * The Master will forward this request to the primary Slave object.
     * The request for a new Frame includes
     * a flag which indicates if a zeroCopy frame is allowed. In most cases this
     * flag can be set to `true`. Non-zero-copy frames are requested if the Master may
     * need to transmit the same frame multiple times.
     * Exposed as `_reqFrame()` in Python.
     *
     * @param size Minimum requested payload size in bytes.
     * @param zeroCopyEn Set to `true` when zero-copy frame allocation is allowed.
     * @return Newly allocated frame pointer.
     */
    std::shared_ptr<rogue::interfaces::stream::Frame> reqFrame(uint32_t size, bool zeroCopyEn);

    /**
     * @brief Sends a frame to all attached slaves.
     *
     * @details
     * This method sends the passed Frame to all of the attached Slave objects by
     * calling their acceptFrame() method. First the secondary Slaves are called in
     * order of attachment, followed last by the primary Slave. If the Frame is a
     * zero copy frame it will most likely be empty when the sendFrame() method returns
     *
     * Exposed as `_sendFrame()` in Python.
     *
     * @param frame Frame to send.
     */
    void sendFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Ensures a frame is represented by a single buffer.
     *
     * @details
     * If the `reqEn` flag is `true` and the passed frame is not a single buffer, a
     * new frame will be requested and the frame data will be copied, with the passed
     * frame pointer being updated. The return value will indicate if the frame is a
     * single buffer at the end of the process. A frame lock must be held when this
     * method is called.
     *
     * Not exposed to Python.
     *
     * @param frame Reference to frame pointer.
     * @param reqEn Set to `true` to allow allocating and copying into a new frame.
     * @return `true` if the resulting frame is single-buffer.
     */
    bool ensureSingleBuffer(std::shared_ptr<rogue::interfaces::stream::Frame>& frame, bool reqEn);

    /**
     * @brief Stops frame generation and shuts down associated threads.
     *
     * @details
     * Exposed as `stop()` in Python.
     *
     * This is the primary subclass hook on `Master`. Override when the
     * subclass owns background activity or transport resources that require
     * deterministic shutdown.
     */
    virtual void stop();

#ifndef NO_PYTHON

    /**
     * @brief Supports `==` operator usage from Python.
     * @param p Python object expected to resolve to a stream `Slave`.
     */
    void equalsPy(boost::python::object p);

    /**
     * @brief Supports `>>` operator usage from Python.
     * @param p Python object expected to resolve to a stream `Slave`.
     * @return Original Python object for chaining semantics.
     */
    boost::python::object rshiftPy(boost::python::object p);

#endif

    /**
     * @brief Supports `==` operator usage in C++.
     * @param other Downstream slave to attach.
     */
    void operator==(std::shared_ptr<rogue::interfaces::stream::Slave>& other);

    /**
     * @brief Connects this master to a slave via stream chaining operator.
     * @param other Downstream slave to attach.
     * @return Reference to `other` for chaining.
     */
    std::shared_ptr<rogue::interfaces::stream::Slave>& operator>>(
        std::shared_ptr<rogue::interfaces::stream::Slave>& other);
};

/** @brief Shared pointer alias for `Master`. */
typedef std::shared_ptr<rogue::interfaces::stream::Master> MasterPtr;
}  // namespace stream
}  // namespace interfaces
}  // namespace rogue
#endif
