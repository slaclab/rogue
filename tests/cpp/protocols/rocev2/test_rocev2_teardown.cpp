/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for the RoCEv2 Server zero-copy teardown lifetime bug.
 *
 * The Server hands frames downstream ZERO-COPY: each rogue Buffer points
 * directly into the registered RX slab (slab_).  A Buffer holds a shared_ptr
 * to its Pool (the Server, see Pool::createBuffer -> Buffer::source_), so the
 * Server object itself always outlives every outstanding Buffer.  The BUG is
 * that the explicit Server::stop() (driven from Python RoCEv2Server._stop())
 * freed slab_ immediately, while frames still queued downstream (a
 * depacketizer / PrbsRx) point into it — a use-after-free.  With the default
 * multi-hundred-KB slab that region is mmap-backed, so free() munmaps it and
 * the later read SIGSEGVs (the "Segmentation fault" seen at GUI close).
 *
 * This test reproduces it deterministically over a single-process Soft-RoCE
 * (rxe0) loopback: a client RC QP SENDs one frame to the Server, a downstream
 * Slave RETAINS the frame, then Server::stop() is called and the retained
 * frame is read back.  On the buggy code the read faults / returns garbage;
 * with the fix (slab freed in ~Server, after all Buffers are gone) the bytes
 * are intact.
 *
 * Hardware-gated: runs only when a Soft-RoCE device named "rxe0" is present
 * (same `if (!rxeAvailable()) return;` skip idiom as test_rocev2.cpp).
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
#include "rogue/Directives.h"

#include <arpa/inet.h>
#include <infiniband/verbs.h>

#include <atomic>
#include <chrono>
#include <cstring>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "doctest/doctest.h"

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/rocev2/Server.h"

namespace rpr = rogue::protocols::rocev2;
namespace ris = rogue::interfaces::stream;

namespace {

constexpr const char* kDev = "rxe0";

// Slab geometry: bufSize_ = maxPayload, slab = maxPayload * rxQueueDepth.
// 4096 * 256 = 1 MiB — comfortably above glibc's default 128 KiB MMAP_THRESHOLD,
// so the slab is large enough to be mmap-backed (mirrors the real ~1 MiB app
// slab).  Whether a premature free() then munmaps the region (buggy read faults)
// or returns it to the allocator arena (buggy read sees stale/reused bytes) is
// allocator- and threshold-dependent, so the test does not rely on a fault; it
// deterministically reclaims the freed region instead (see the clobber below).
constexpr uint32_t kMaxPayload   = 4096;
constexpr uint32_t kQueueDepth   = 256;
constexpr uint32_t kMinRnrTimer  = 12;
constexpr uint32_t kPayloadLen   = 1024;   // bytes actually SENT (<= bufSize_)
// path_mtu is chosen at runtime from the port's active_mtu: rxe0 inherits the
// backing netdev MTU (typically 1500 -> IBV_MTU_1024), so a fixed 4096 would be
// rejected at INIT->RTR. The RC layer segments the SEND into path_mtu packets;
// the receive slot (bufSize_ = maxPayload) still holds the reassembled payload.
constexpr uint32_t kClientSqPsn  = 0x000100;

// Runtime probe: true iff an ibverbs device named "rxe0" is registered.
bool rxeAvailable() {
    int          num  = 0;
    ibv_device** list = ibv_get_device_list(&num);
    if (!list) return false;
    bool found = false;
    for (int i = 0; i < num; ++i) {
        if (std::string(kDev) == ibv_get_device_name(list[i])) {
            found = true;
            break;
        }
    }
    ibv_free_device_list(list);
    return found;
}

// First GID-table index whose GID is IPv4-mapped (::ffff:a.b.c.d) and non-zero.
// rxe0 index 0 is the link-local fe80:: GID and RTR is rejected with it; the
// IPv4-mapped GID on the netdev's subnet is the RoCEv2 data-plane GID (the same
// one the app's RoCEv2Server.detectGidIndex picks).
int findIpv4GidIndex(ibv_context* ctx, uint8_t port) {
    // gid_tbl_len is device-dependent and can be large (rdma_rxe reports 1024,
    // see Server.cpp) — the IPv4-mapped GID is not guaranteed to land in the
    // first handful of slots, so scan the whole table rather than a fixed 16.
    ibv_port_attr pattr;
    memset(&pattr, 0, sizeof(pattr));
    if (ibv_query_port(ctx, port, &pattr) != 0) return -1;
    for (int i = 0; i < pattr.gid_tbl_len; ++i) {
        ibv_gid g;
        if (ibv_query_gid(ctx, port, i, &g) != 0) continue;
        // Match the full IPv4-mapped prefix ::ffff:0:0/96 — bytes[0..9] must be
        // zero and bytes[10..11] == 0xffff — so a non-IPv4-mapped GID whose
        // bytes[0..9] happen to be non-zero cannot be mistaken for one.
        bool prefixZero = true;
        for (int b = 0; b < 10; ++b) {
            if (g.raw[b] != 0) {
                prefixZero = false;
                break;
            }
        }
        if (prefixZero && g.raw[10] == 0xff && g.raw[11] == 0xff &&
            (g.raw[12] | g.raw[13] | g.raw[14] | g.raw[15]) != 0)
            return i;
    }
    return -1;
}

// Downstream Slave that RETAINS every frame — the depacketizer/PrbsRx stand-in
// that still holds a zero-copy buffer when the Server tears down.
class HoldingSlave : public ris::Slave {
  public:
    void acceptFrame(ris::FramePtr frame) override {
        std::lock_guard<std::mutex> lk(mtx_);
        frames_.push_back(frame);
    }
    size_t count() {
        std::lock_guard<std::mutex> lk(mtx_);
        return frames_.size();
    }
    ris::FramePtr front() {
        std::lock_guard<std::mutex> lk(mtx_);
        return frames_.empty() ? nullptr : frames_.front();
    }

  private:
    std::mutex                 mtx_;
    std::vector<ris::FramePtr> frames_;
};

// Minimal loopback client: an RC QP on rxe0 that SENDs one frame to the Server.
// Raw ibverbs (rogue has no TX Server); torn down by destroy().  destroy() is
// idempotent and also runs from the destructor, so a REQUIRE() failure part-way
// through open()/connectTo() still releases every ibverbs kernel object as the
// stack unwinds.  Copy/assign are deleted to prevent a double-free of the raw
// owning handles.
struct LoopbackClient {
    ibv_context* ctx = nullptr;
    ibv_pd*      pd  = nullptr;
    ibv_cq*      cq  = nullptr;
    ibv_qp*      qp  = nullptr;
    ibv_mr*      mr  = nullptr;
    std::vector<uint8_t> sbuf;
    ibv_gid  gid{};
    uint8_t  gidIndex = 0;

    LoopbackClient()  = default;
    ~LoopbackClient() { destroy(); }
    LoopbackClient(const LoopbackClient&)            = delete;
    LoopbackClient& operator=(const LoopbackClient&) = delete;

    bool open() {
        int          num  = 0;
        ibv_device** list = ibv_get_device_list(&num);
        if (!list) return false;
        ibv_device* dev = nullptr;
        for (int i = 0; i < num; ++i) {
            if (std::string(kDev) == ibv_get_device_name(list[i])) {
                dev = list[i];
                break;
            }
        }
        if (dev) ctx = ibv_open_device(dev);
        ibv_free_device_list(list);
        if (!ctx) return false;

        pd = ibv_alloc_pd(ctx);
        if (!pd) return false;
        cq = ibv_create_cq(ctx, 16, nullptr, nullptr, 0);
        if (!cq) return false;

        sbuf.assign(kPayloadLen, 0);
        for (uint32_t i = 0; i < kPayloadLen; ++i)
            sbuf[i] = static_cast<uint8_t>((i * 7 + 3) & 0xFF);   // deterministic pattern
        mr = ibv_reg_mr(pd, sbuf.data(), kPayloadLen, IBV_ACCESS_LOCAL_WRITE);
        if (!mr) return false;

        ibv_qp_init_attr ia;
        memset(&ia, 0, sizeof(ia));
        ia.qp_type          = IBV_QPT_RC;
        ia.send_cq          = cq;
        ia.recv_cq          = cq;
        ia.cap.max_send_wr  = 4;
        ia.cap.max_recv_wr  = 4;
        ia.cap.max_send_sge = 1;
        ia.cap.max_recv_sge = 1;
        qp = ibv_create_qp(pd, &ia);
        if (!qp) return false;

        return true;
    }

    // Query + store the GID at `idx` and remember idx for the AH sgid_index.
    // On rxe0 loopback this GID is both the client's source GID and (same
    // device/index) the Server's destination GID.
    bool queryGid(uint8_t idx) {
        gidIndex = idx;
        if (ibv_query_gid(ctx, 1, idx, &gid) != 0) return false;
        for (int i = 0; i < 16; ++i)
            if (gid.raw[i]) return true;   // non-zero GID
        return false;
    }

    // Move client QP INIT -> RTR -> RTS aimed at the Server's QP.
    bool connectTo(uint32_t serverQpn, uint32_t serverSqPsn, uint32_t pmtu) {
        {   // INIT
            ibv_qp_attr a;
            memset(&a, 0, sizeof(a));
            a.qp_state        = IBV_QPS_INIT;
            a.pkey_index      = 0;
            a.port_num        = 1;
            a.qp_access_flags = IBV_ACCESS_LOCAL_WRITE | IBV_ACCESS_REMOTE_WRITE |
                                IBV_ACCESS_REMOTE_READ;
            if (ibv_modify_qp(qp, &a, IBV_QP_STATE | IBV_QP_PKEY_INDEX |
                                          IBV_QP_PORT | IBV_QP_ACCESS_FLAGS))
                return false;
        }
        {   // RTR — dest = Server QP; our RQ expects the Server's SQ PSN
            ibv_qp_attr a;
            memset(&a, 0, sizeof(a));
            a.qp_state           = IBV_QPS_RTR;
            a.path_mtu           = static_cast<ibv_mtu>(pmtu);
            a.dest_qp_num        = serverQpn;
            a.rq_psn             = serverSqPsn;
            a.max_dest_rd_atomic = 1;
            a.min_rnr_timer      = kMinRnrTimer;
            a.ah_attr.is_global      = 1;
            a.ah_attr.grh.dgid       = gid;   // loopback: Server GID == our GID
            a.ah_attr.grh.sgid_index = gidIndex;
            a.ah_attr.grh.hop_limit  = 64;
            a.ah_attr.port_num       = 1;
            a.ah_attr.sl             = 0;
            if (ibv_modify_qp(qp, &a, IBV_QP_STATE | IBV_QP_AV | IBV_QP_PATH_MTU |
                                          IBV_QP_DEST_QPN | IBV_QP_RQ_PSN |
                                          IBV_QP_MAX_DEST_RD_ATOMIC | IBV_QP_MIN_RNR_TIMER))
                return false;
        }
        {   // RTS — our SQ PSN must match the Server's RQ PSN (= kClientSqPsn)
            ibv_qp_attr a;
            memset(&a, 0, sizeof(a));
            a.qp_state      = IBV_QPS_RTS;
            a.sq_psn        = kClientSqPsn;
            a.timeout       = 14;
            a.retry_cnt     = 7;
            a.rnr_retry     = 7;
            a.max_rd_atomic = 1;
            if (ibv_modify_qp(qp, &a, IBV_QP_STATE | IBV_QP_SQ_PSN | IBV_QP_TIMEOUT |
                                          IBV_QP_RETRY_CNT | IBV_QP_RNR_RETRY |
                                          IBV_QP_MAX_QP_RD_ATOMIC))
                return false;
        }
        return true;
    }

    // One RDMA SEND-with-immediate.  imm low byte = channel (Server decodes
    // ntohl(imm) & 0xFF); 0 is fine.
    bool send() {
        ibv_sge sge;
        memset(&sge, 0, sizeof(sge));
        sge.addr   = reinterpret_cast<uint64_t>(sbuf.data());
        sge.length = kPayloadLen;
        sge.lkey   = mr->lkey;

        ibv_send_wr wr;
        memset(&wr, 0, sizeof(wr));
        wr.wr_id      = 1;
        wr.sg_list    = &sge;
        wr.num_sge    = 1;
        wr.opcode     = IBV_WR_SEND_WITH_IMM;
        wr.send_flags = IBV_SEND_SIGNALED;
        wr.imm_data   = htonl(0);   // channel 0

        ibv_send_wr* bad = nullptr;
        return ibv_post_send(qp, &wr, &bad) == 0;
    }

    void destroy() {
        if (qp) {
            ibv_destroy_qp(qp);
            qp = nullptr;
        }
        if (mr) {
            ibv_dereg_mr(mr);
            mr = nullptr;
        }
        if (cq) {
            ibv_destroy_cq(cq);
            cq = nullptr;
        }
        if (pd) {
            ibv_dealloc_pd(pd);
            pd = nullptr;
        }
        if (ctx) {
            ibv_close_device(ctx);
            ctx = nullptr;
        }
    }
};

}  // namespace

TEST_CASE("rocev2 Server::stop must not free the RX slab while a zero-copy frame is held") {
    if (!rxeAvailable()) return;  // runtime-skip idiom (doctest 2.4.12 has no skip macro)

    // Loopback client — open first so we can pick a GID index usable by both.
    LoopbackClient client;
    REQUIRE(client.open());

    // Use the IPv4-mapped RoCEv2 GID (skip the link-local fe80:: at index 0,
    // which rxe rejects at INIT->RTR). Same index for the Server and client.
    const int gidIdx = findIpv4GidIndex(client.ctx, 1);
    REQUIRE(gidIdx >= 0);
    // sgid_index (ibv_ah_attr.grh) and Server::create's gidIndex are both
    // uint8_t, so an index past 255 (gid_tbl_len can be 1024) would silently
    // truncate and test the wrong GID.  Bound-check, then use one uint8_t value.
    REQUIRE(gidIdx <= 255);
    const uint8_t gidIndex = static_cast<uint8_t>(gidIdx);
    REQUIRE(client.queryGid(gidIndex));

    // Server (receiver) on rxe0 at the IPv4-mapped GID index.
    auto server = rpr::Server::create(kDev, 1, gidIndex, kMaxPayload, kQueueDepth);
    REQUIRE(server != nullptr);

    auto slave = std::make_shared<HoldingSlave>();
    server->addSlave(slave);

    // path_mtu = the port's active MTU (rxe0 inherits the netdev MTU); a fixed
    // 4096 is rejected at INIT->RTR when the netdev MTU is smaller.
    ibv_port_attr pattr;
    memset(&pattr, 0, sizeof(pattr));
    REQUIRE(ibv_query_port(client.ctx, 1, &pattr) == 0);
    const uint32_t pmtu = static_cast<uint32_t>(pattr.active_mtu);  // IBV_MTU_* enum

    // Tell the Server about the client, then bring both QPs to RTS.  The
    // Server's RQ PSN is set to kClientSqPsn (its completeConnection second
    // arg = remote SQ start); the client's RQ PSN tracks the Server SQ PSN.
    std::string clientGid(reinterpret_cast<const char*>(client.gid.raw), 16);
    server->setFpgaGid(clientGid);
    server->completeConnection(client.qp->qp_num, kClientSqPsn, pmtu, kMinRnrTimer);
    REQUIRE(client.connectTo(server->getQpn(), server->getSqPsn(), pmtu));

    REQUIRE(client.send());

    // Wait (bounded) for the Server's receive thread to deliver the frame.
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
    while (slave->count() == 0 && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    REQUIRE(slave->count() >= 1);

    ris::FramePtr frame = slave->front();
    REQUIRE(frame != nullptr);
    REQUIRE(frame->getPayload() == kPayloadLen);

    // Read the zero-copy payload BEFORE teardown — sanity that the frame really
    // carried our SEND straight out of the slab.
    std::vector<uint8_t> before(kPayloadLen);
    {
        auto it = frame->beginRead();
        ris::fromFrame(it, kPayloadLen, before.data());
    }
    CHECK_EQ(std::memcmp(before.data(), client.sbuf.data(), kPayloadLen), 0);

    // TEARDOWN while `frame` is still held downstream.  On the buggy build
    // Server::stop() -> cleanupResources() free()s the slab that `frame` still
    // points into.  (Fixed build: the slab is freed only in ~Server, which the
    // frame's shared_ptr<Pool> keeps alive, so it outlives the frame.)
    server->stop();

    // Reclaim the freed region: many same-size allocations, each fully written,
    // so the allocator hands the just-freed slab chunk back and we overwrite it.
    // A premature free() may munmap the slab (a later read then faults) or return
    // it to the allocator arena (the stale bytes linger until reused) depending on
    // the allocator and its mmap threshold; this clobber is a best-effort provoke
    // of reuse so the failure is a deterministic byte mismatch when it does not
    // fault outright.  On the fixed build the slab is still live, so these land
    // elsewhere and the frame is untouched.
    const size_t slabBytes = static_cast<size_t>(kMaxPayload) * kQueueDepth;
    std::vector<std::vector<uint8_t>> clobber;
    clobber.reserve(64);   // avoid outer-vector regrowth during the loop
    for (int i = 0; i < 64; ++i)
        clobber.emplace_back(slabBytes, 0xAA);

    // Re-read the SAME frame.  Fixed build: slab intact -> bytes still match.
    // Buggy build: use-after-free -> bytes are the 0xAA clobber (or a fault).
    std::vector<uint8_t> after(kPayloadLen, 0);
    {
        auto it = frame->beginRead();
        ris::fromFrame(it, kPayloadLen, after.data());
    }
    CHECK_EQ(std::memcmp(after.data(), client.sbuf.data(), kPayloadLen), 0);

    // Release the held frame before the client MR/QP it (indirectly) races.
    frame.reset();
    client.destroy();
}
