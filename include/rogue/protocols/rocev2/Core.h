/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *   RoCEv2 Core Class
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

#ifndef __ROGUE_PROTOCOLS_ROCEV2_CORE_H__
#define __ROGUE_PROTOCOLS_ROCEV2_CORE_H__
#include "rogue/Directives.h"

#include <infiniband/verbs.h>
#include <memory>
#include <stdint.h>
#include <string>

#include "rogue/Logging.h"

namespace rogue {
namespace protocols {
namespace rocev2 {

// Number of receive work requests to keep posted at all times.
// Increase if you see CQ overruns at high data rates.
static const uint32_t DefaultRxQueueDepth = 256;

// Maximum transfer unit for a single RDMA WRITE operation.
// Must be large enough for the biggest frame your FPGA will send.
// Default: 9000 bytes (jumbo-frame equivalent).
static const uint32_t DefaultMaxPayload = 9000;

class Core {
  protected:
    // ibverbs resources owned by Core.  CQ / QP / MR are owned by Server
    // and live in the derived class.
    struct ibv_context* ctx_;   // device context
    struct ibv_pd*      pd_;    // protection domain

    // Configuration
    std::string  deviceName_;   // e.g. "rxe0" or "mlx5_0"
    uint8_t      ibPort_;       // ibverbs port number (almost always 1)
    uint8_t      gidIndex_;     // GID table index for RoCEv2 (IPv4/IPv6)
    uint32_t     maxPayload_;   // max bytes per RDMA WRITE

    std::shared_ptr<rogue::Logging> log_;

  public:
    Core(const std::string& deviceName,
         uint8_t            ibPort,
         uint8_t            gidIndex,
         uint32_t           maxPayload = DefaultMaxPayload);

    virtual ~Core();

    uint32_t maxPayload() const { return maxPayload_; }

    static void setup_python();
};

typedef std::shared_ptr<rogue::protocols::rocev2::Core> CorePtr;

}  // namespace rocev2
}  // namespace protocols
}  // namespace rogue

#endif  // __ROGUE_PROTOCOLS_ROCEV2_CORE_H__
