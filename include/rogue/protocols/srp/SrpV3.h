/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    SLAC Register Protocol (SRP) SrpV3
 *-----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 * https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 *-----------------------------------------------------------------------------
 **/
#ifndef __ROGUE_PROTOCOLS_SRP_SRPV3_H__
#define __ROGUE_PROTOCOLS_SRP_SRPV3_H__
#include "rogue/Directives.h"

#include <stdint.h>

#include <memory>
#include <thread>

#include "rogue/Logging.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"

namespace rogue {
namespace protocols {
namespace srp {

/**
 * @brief SRP v3 bridge between Rogue memory transactions and stream frames.
 *
 * @details
 * `SrpV3` sits between the memory interface (`memory::Slave`) and stream
 * transport (`stream::Master`/`stream::Slave`). It serializes memory read/write
 * transactions into SRP v3 request frames and decodes incoming SRP responses to
 * complete transactions.
 *
 * SRP frames are stream transactions carried over a physical/link transport
 * (for example DMA, TCP, or other Rogue stream backends) before arriving at an
 * FPGA or ASIC endpoint that implements the SRP protocol for register access.
 *
 * Implementation behavior:
 * - `doTransaction()` serializes each memory request into one SRPv3 frame and
 *   transmits it immediately.
 * - Non-posted transactions are registered in the base `memory::Slave`
 *   in-flight transaction map (`addTransaction()`), keyed by transaction ID.
 * - Multiple requests may be transmitted before any responses arrive, so
 *   multiple transactions can be in flight concurrently.
 * - `acceptFrame()` extracts the response ID and resolves it with
 *   `getTransaction(id)`, so responses are matched by ID and may arrive out of
 *   order without violating correctness.
 *
 * Threading/locking model:
 * - In-flight map access is protected by the `memory::Slave` mutex.
 * - Per-transaction payload/state access is protected by `TransactionLock`.
 * - `doTransaction()` and `acceptFrame()` can be called from different runtime
 *   contexts provided by the connected stream transport stack.
 *
 * Missing, late, or invalid responses:
 * - Software wait timeout is enforced by the initiating `memory::Master`
 *   transaction timeout (`Master::setTimeout()` in microseconds).
 * - If no valid response arrives before timeout, the waiting side completes
 *   with a timeout error.
 * - If a late response arrives after timeout, it is treated as expired and
 *   ignored.
 * - If a response has unknown ID, malformed header/size, or hardware error
 *   status in tail bits, the response is rejected. For matched transactions,
 *   protocol/tail/size errors are reported immediately; unknown-ID responses
 *   are dropped and do not complete any in-flight transaction.
 *
 * Compared with earlier protocol versions, v3 has a different header format and
 * supports a configurable protocol timeout field through `setHardwareTimeout()`.
 * This hardware timeout field is encoded into outgoing SRPv3 requests and is
 * separate from Rogue software-side wait timeout behavior.
 *
 * Protocol reference:
 * https://confluence.slac.stanford.edu/x/cRmVD
 */
class SrpV3 : public rogue::interfaces::stream::Master,
              public rogue::interfaces::stream::Slave,
              public rogue::interfaces::memory::Slave {
    std::shared_ptr<rogue::Logging> log_;

    static const uint32_t HeadLen = 20;
    static const uint32_t TailLen = 4;

    uint8_t timeout_ = 0x0A;

    // Setup header, return write flag
    bool setupHeader(std::shared_ptr<rogue::interfaces::memory::Transaction> tran,
                     uint32_t* header,
                     uint32_t& frameLen,
                     bool tx);

  public:
    /**
     * @brief Creates an SRP v3 interface instance.
     *
     * @details
     * This static factory is the preferred construction path when the object
     * is shared across Rogue graph connections or exposed to Python.
     * It returns `std::shared_ptr` ownership compatible with Rogue pointer typedefs.
     *
     * @return Shared pointer to the created `SrpV3`.
     */
    static std::shared_ptr<rogue::protocols::srp::SrpV3> create();

    /** @brief Registers Python bindings for this class. */
    static void setup_python();

    /**
     * @brief Constructs an SRP v3 interface instance.
     *
     * @details
     * This constructor is a low-level C++ allocation path.
     * Prefer `create()` when shared ownership or Python exposure is required.
     */
    SrpV3();

    /** @brief Destroys the SRP v3 interface instance. */
    ~SrpV3();

    /**
     * @brief Processes a memory transaction and emits SRP v3 request frame(s).
     *
     * @details
     * Called by upstream memory masters. Transaction fields are encoded in SRP v3
     * format and transmitted through the stream master connection.
     *
     * @param tran Transaction to execute over SRP.
     */
    void doTransaction(std::shared_ptr<rogue::interfaces::memory::Transaction> tran);

    /**
     * @brief Accepts an incoming SRP v3 response frame.
     *
     * @details
     * Decodes the frame, associates it with the corresponding pending transaction,
     * and propagates status/data completion.
     *
     * @param frame Received SRP stream frame.
     */
    void acceptFrame(std::shared_ptr<rogue::interfaces::stream::Frame> frame);

    /**
     * @brief Sets SRP hardware timeout field used in outgoing requests.
     *
     * @details
     * The encoded timeout value is protocol-specific and interpreted by the
     * remote SRP endpoint.
     *
     * @param val Timeout field value to encode into request header(s).
     */
    void setHardwareTimeout(uint8_t val);
};

// Convenience
typedef std::shared_ptr<rogue::protocols::srp::SrpV3> SrpV3Ptr;
}  // namespace srp
}  // namespace protocols
}  // namespace rogue
#endif
