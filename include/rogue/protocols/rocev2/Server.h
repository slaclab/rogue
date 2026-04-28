/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 *   RoCEv2 Server Class
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

#ifndef __ROGUE_PROTOCOLS_ROCEV2_SERVER_H__
#define __ROGUE_PROTOCOLS_ROCEV2_SERVER_H__
#include "rogue/Directives.h"

#include <infiniband/verbs.h>
#include <stdint.h>

#include <atomic>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Pool.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/rocev2/Core.h"

namespace rogue {
namespace protocols {
namespace rocev2 {

class Server : public rogue::protocols::rocev2::Core,
               public rogue::interfaces::stream::Master,
               public rogue::interfaces::stream::Slave {
  private:
    // -----------------------------------------------------------------------
    // ibverbs resources
    // -----------------------------------------------------------------------
    struct ibv_cq* cq_;
    struct ibv_qp* qp_;
    struct ibv_mr* mr_;

    // Contiguous slab — subdivided into numBufs_ fixed-size slots.
    // Registered with the HCA once; never copied from.
    uint8_t*  slab_;
    uint32_t  slabSize_;
    uint32_t  numBufs_;
    uint32_t  bufSize_;       // == maxPayload_ (no GRH on RC)

    // -----------------------------------------------------------------------
    // Host-side RC parameters.  All initialized to 0 in the member-init list
    // so an early throw inside the ctor body cannot leave a reader of the
    // getters (e.g. a getXxx() hooked into a LocalVariable's localGet in the
    // failed-construction propagation path) observing indeterminate values.
    // Real values are written inside the ctor body as each ibverbs stage
    // completes successfully.
    // -----------------------------------------------------------------------
    uint32_t hostQpn_;
    uint8_t  hostGid_[16];
    uint32_t hostRqPsn_;
    uint32_t hostSqPsn_;
    uint64_t mrAddr_;
    uint32_t mrRkey_;

    // FPGA GID — set by setFpgaGid() before completeConnection()
    uint8_t  fpgaGid_[16];

    // -----------------------------------------------------------------------
    // Receive thread
    // -----------------------------------------------------------------------
    std::thread*      thread_;
    std::atomic<bool> threadEn_;

    // Intentional shadow: both Core and stream::Slave expose a `log_` member,
    // so any unqualified `log_` from inside Server would otherwise be
    // ambiguous.  Declaring our own `log_` here consolidates both names onto
    // Server's "rocev2.Server" logger (assigned in the Server ctor) and
    // silences the multiple-inheritance ambiguity.
    std::shared_ptr<rogue::Logging> log_;

    // RX counters
    std::atomic<uint64_t> frameCount_;
    std::atomic<uint64_t> byteCount_;

    void postRecvWr(uint32_t slot);
    void runThread(std::weak_ptr<int> lockPtr);

    // Idempotent helper that releases every ibverbs / heap resource owned by
    // Server in reverse allocation order.  Called by stop() and from the
    // failed-construction path in the constructor.
    void cleanupResources();

  protected:
    // -----------------------------------------------------------------------
    // Zero-copy hook — called by Buffer::~Buffer() when the last downstream
    // reference to a frame is released.  Re-posts the slab slot to the QP.
    // The slot index is encoded in the lower 24 bits of meta.
    // -----------------------------------------------------------------------
    void retBuffer(uint8_t* data, uint32_t meta, uint32_t rawSize) override;

  public:
    static std::shared_ptr<rogue::protocols::rocev2::Server> create(
        const std::string& deviceName,
        uint8_t            ibPort,
        uint8_t            gidIndex,
        uint32_t           maxPayload   = DefaultMaxPayload,
        uint32_t           rxQueueDepth = DefaultRxQueueDepth);

    Server(const std::string& deviceName,
           uint8_t            ibPort,
           uint8_t            gidIndex,
           uint32_t           maxPayload,
           uint32_t           rxQueueDepth);

    ~Server();
    void stop();

    void setFpgaGid(const std::string& gidBytes);

    // minRnrTimer: IB spec RNR timer code embedded in RNR NAK packets.
    //   1=0.01ms  14=1ms  18=4ms  22=16ms  31=491ms
    void completeConnection(uint32_t fpgaQpn,
                            uint32_t fpgaRqPsn,
                            uint32_t pmtu        = 5,
                            uint32_t minRnrTimer = 1);

    uint32_t    getQpn()        const { return hostQpn_; }
    std::string getGid()        const;
    uint32_t    getRqPsn()      const { return hostRqPsn_; }
    uint32_t    getSqPsn()      const { return hostSqPsn_; }
    uint64_t    getMrAddr()     const { return mrAddr_; }
    uint32_t    getMrRkey()     const { return mrRkey_; }
    uint64_t    getFrameCount() const { return frameCount_.load(); }
    uint64_t    getByteCount()  const { return byteCount_.load(); }

    void acceptFrame(rogue::interfaces::stream::FramePtr frame) override;

    static void setup_python();
};

typedef std::shared_ptr<rogue::protocols::rocev2::Server> ServerPtr;

}  // namespace rocev2
}  // namespace protocols
}  // namespace rogue

#endif
