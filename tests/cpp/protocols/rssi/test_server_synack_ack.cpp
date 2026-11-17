/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: a server's SYN-ACK, and every frame it sends before its
 * application thread has delivered anything, acknowledges the client's SYN
 * sequence. stateSendSynAck() used to leave ackSeqRx_ at its initial value of
 * 0, so the server acknowledged 0 until the first data frame was popped on
 * the application side. The client path, stateSendSeqAck(), already seeds it.
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
#include <stdint.h>

#include <memory>
#include <mutex>
#include <vector>

#include "doctest/doctest.h"
#include "support/test_helpers.h"

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Pool.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/rssi/Header.h"
#include "rogue/protocols/rssi/Server.h"
#include "rogue/protocols/rssi/Transport.h"

namespace ris = rogue::interfaces::stream;
namespace rpr = rogue::protocols::rssi;

namespace {

// Decoded view of one frame the server transmitted.
struct TxRecord {
    bool syn;
    bool ack;
    bool nul;
    uint8_t sequence;
    uint8_t acknowledge;
};

// Fake remote client. Supplies transmit buffers to the server transport and
// records every header the server sends.
class FakePeer : public ris::Slave {
  public:
    void acceptFrame(ris::FramePtr frame) override {
        rpr::HeaderPtr head    = rpr::Header::create(frame);
        ris::FrameLockPtr lock = frame->lock();
        if (!head->verify()) return;
        TxRecord rec{head->syn, head->ack, head->nul, head->sequence, head->acknowledge};
        lock->unlock();

        std::lock_guard<std::mutex> guard(mutex_);
        records_.push_back(rec);
    }

    std::vector<TxRecord> records() {
        std::lock_guard<std::mutex> guard(mutex_);
        return records_;
    }

    bool findSynAck(TxRecord& out) {
        return find([](const TxRecord& rec) { return rec.syn && rec.ack; }, out);
    }

    bool findNull(TxRecord& out) {
        return find([](const TxRecord& rec) { return rec.nul; }, out);
    }

  private:
    template <class Pred>
    bool find(Pred pred, TxRecord& out) {
        std::lock_guard<std::mutex> guard(mutex_);
        for (const TxRecord& rec : records_) {
            if (pred(rec)) {
                out = rec;
                return true;
            }
        }
        return false;
    }

    std::mutex mutex_;
    std::vector<TxRecord> records_;
};

// The client's SYN sequence. Distinct from the controller's initial
// ackSeqRx_ of 0 and from its own initial locSequence_ of 100.
const uint8_t ClientSequence = 50;

// Protocol version and timeout unit (milliseconds) advertised by rpr::Controller.
const uint8_t RssiVersion     = 1;
const uint8_t RssiTimeoutUnit = 3;

// Deliver the client's SYN to the server transport. The short NULL timeout
// makes the server send a NULL soon after opening, before any data.
void injectSyn(const rpr::TransportPtr& transport, const std::shared_ptr<ris::Pool>& pool) {
    rpr::HeaderPtr head          = rpr::Header::create(pool->acceptReq(rpr::Header::SynSize, false));
    head->syn                    = true;
    head->ack                    = false;
    head->rst                    = false;
    head->nul                    = false;
    head->busy                   = false;
    head->sequence               = ClientSequence;
    head->acknowledge            = 0;
    head->version                = RssiVersion;
    head->chk                    = true;
    head->maxOutstandingSegments = 8;
    head->maxSegmentSize         = 1024;
    head->retransmissionTimeout  = 20;
    head->cumulativeAckTimeout   = 5;
    head->nullTimeout            = 30;
    head->maxRetransmissions     = 15;
    head->maxCumulativeAck       = 2;
    head->timeoutUnit            = RssiTimeoutUnit;
    head->connectionId           = 0x11223344;
    head->update();
    transport->acceptFrame(head->getFrame());
}

}  // namespace

TEST_CASE("rpr::Server acknowledges the client's SYN sequence before any data arrives") {
    std::shared_ptr<FakePeer> peer  = std::make_shared<FakePeer>();
    std::shared_ptr<ris::Pool> pool = rogue_test::makePool();
    rpr::ServerPtr server           = rpr::Server::create(1024);

    server->transport()->addSlave(peer);
    server->start();

    // The server thread accepts a SYN only once it has moved from StClosed to
    // StWaitSyn, so a SYN injected right after start() can be dropped on a
    // slow host. Retry it the way a real client does until the SYN-ACK shows.
    TxRecord synAck{};
    bool gotSynAck = false;
    for (uint32_t attempt = 0; attempt < 5 && !gotSynAck; attempt++) {
        injectSyn(server->transport(), pool);
        gotSynAck = rogue_test::waitUntil([&] { return peer->findSynAck(synAck); }, 500);
    }
    REQUIRE(gotSynAck);
    CHECK_EQ(synAck.acknowledge, ClientSequence);
    REQUIRE(rogue_test::waitUntil([&] { return server->getOpen(); }, 2000));

    // The first NULL keepalive goes out before the application side has
    // delivered anything, so it must still acknowledge the SYN sequence.
    TxRecord nul{};
    REQUIRE(rogue_test::waitUntil([&] { return peer->findNull(nul); }, 2000));
    CHECK_EQ(nul.acknowledge, ClientSequence);

    // Nothing the server sent so far may carry a different acknowledge.
    for (const TxRecord& rec : peer->records()) {
        CHECK(rec.ack);
        CHECK_EQ(rec.acknowledge, ClientSequence);
    }

    server->stop();
}
