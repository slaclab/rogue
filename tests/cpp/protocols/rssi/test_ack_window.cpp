/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: rpr::Controller::transportRx() only accepts acknowledgements
 * that fall inside the outstanding transmit window (lastAckRx_, locSequence_).
 * A stale or out of window ack must leave txList_ intact so the unacknowledged
 * frames are still retransmitted, and a valid cumulative ack must still
 * release them.
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

#include <chrono>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "support/test_helpers.h"

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Pool.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Client.h"
#include "rogue/protocols/rssi/Header.h"
#include "rogue/protocols/rssi/Transport.h"

namespace ris = rogue::interfaces::stream;
namespace rpr = rogue::protocols::rssi;

namespace {

// Decoded view of one frame the client transmitted.
struct TxRecord {
    bool syn;
    bool ack;
    bool nul;
    bool rst;
    uint8_t sequence;
    uint8_t acknowledge;
    uint32_t payload;

    bool isData() const {
        return !syn && !nul && !rst && payload > static_cast<uint32_t>(rpr::Header::HeaderSize);
    }
};

// Fake remote peer. Supplies transmit buffers to the client transport and
// records every header the client sends. Frames are left untouched since the
// client keeps them for retransmission.
class FakePeer : public ris::Slave {
  public:
    void acceptFrame(ris::FramePtr frame) override {
        rpr::HeaderPtr head    = rpr::Header::create(frame);
        ris::FrameLockPtr lock = frame->lock();
        if (!head->verify()) return;
        TxRecord
            rec{head->syn, head->ack, head->nul, head->rst, head->sequence, head->acknowledge, frame->getPayload()};
        lock->unlock();

        std::lock_guard<std::mutex> guard(mutex_);
        records_.push_back(rec);
    }

    // Number of data frames transmitted with the given sequence.
    uint32_t dataCount(uint8_t sequence) {
        std::lock_guard<std::mutex> guard(mutex_);
        uint32_t count = 0;
        for (const TxRecord& rec : records_) {
            if (rec.isData() && rec.sequence == sequence) count++;
        }
        return count;
    }

    bool findSyn(TxRecord& out) {
        std::lock_guard<std::mutex> guard(mutex_);
        for (const TxRecord& rec : records_) {
            if (rec.syn && !rec.ack) {
                out = rec;
                return true;
            }
        }
        return false;
    }

  private:
    std::mutex mutex_;
    std::vector<TxRecord> records_;
};

const uint8_t PeerSequence = 50;

// Protocol version and timeout unit (milliseconds) advertised by rpr::Controller.
const uint8_t RssiVersion     = 1;
const uint8_t RssiTimeoutUnit = 3;

void sleepMs(uint32_t ms) {
    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}

// Build a header frame as the fake peer and deliver it to the client transport.
void inject(const rpr::TransportPtr& transport, const rpr::HeaderPtr& head) {
    head->update();
    transport->acceptFrame(head->getFrame());
}

rpr::HeaderPtr makeHeader(const std::shared_ptr<ris::Pool>& pool, bool syn) {
    uint32_t size       = syn ? rpr::Header::SynSize : static_cast<uint32_t>(rpr::Header::HeaderSize);
    rpr::HeaderPtr head = rpr::Header::create(pool->acceptReq(size, false));
    head->syn           = syn;
    head->ack           = false;
    head->rst           = false;
    head->nul           = false;
    head->busy          = false;
    head->sequence      = PeerSequence;
    head->acknowledge   = 0;
    return head;
}

void injectSynAck(const rpr::TransportPtr& transport, const std::shared_ptr<ris::Pool>& pool, uint8_t clientSynSeq) {
    rpr::HeaderPtr head          = makeHeader(pool, true);
    head->ack                    = true;
    head->acknowledge            = clientSynSeq;
    head->version                = RssiVersion;
    head->chk                    = true;
    head->maxOutstandingSegments = 8;
    head->maxSegmentSize         = 1024;
    head->retransmissionTimeout  = 20;
    head->cumulativeAckTimeout   = 5;
    head->nullTimeout            = 10000;  // Keep NULL keepalives out of the sequence space during the test
    head->maxRetransmissions     = 15;
    head->maxCumulativeAck       = 2;
    head->timeoutUnit            = RssiTimeoutUnit;
    head->connectionId           = 0x11223344;
    inject(transport, head);
}

void injectAck(const rpr::TransportPtr& transport, const std::shared_ptr<ris::Pool>& pool, uint8_t acknowledge) {
    rpr::HeaderPtr head = makeHeader(pool, false);
    head->ack           = true;
    head->acknowledge   = acknowledge;
    inject(transport, head);
}

void sendData(const rpr::ApplicationPtr& app, uint8_t fill) {
    ris::FramePtr frame = app->acceptReq(16, false);
    rogue_test::writeFrame(frame, std::vector<uint8_t>(16, fill));
    app->acceptFrame(frame);
}

struct Fixture {
    std::shared_ptr<FakePeer> peer  = std::make_shared<FakePeer>();
    std::shared_ptr<ris::Pool> pool = rogue_test::makePool();
    rpr::ClientPtr client           = rpr::Client::create(1024);
    uint8_t synSeq                  = 0;

    Fixture() {
        client->transport()->addSlave(peer);
        client->setLocTryPeriod(20);
        client->setLocRetranTout(20);
        client->start();

        // Complete the SYN handshake as the peer.
        TxRecord syn{};
        REQUIRE(rogue_test::waitUntil([&] { return peer->findSyn(syn); }, 2000));
        synSeq = syn.sequence;
        injectSynAck(client->transport(), pool, synSeq);
        REQUIRE(rogue_test::waitUntil([&] { return client->getOpen(); }, 2000));
    }

    ~Fixture() {
        client.reset();
    }

    // Send two data frames and wait until both are on the wire once.
    void sendTwo() {
        sendData(client->application(), 0xA5);
        sendData(client->application(), 0x5A);
        REQUIRE(
            rogue_test::waitUntil([&] { return peer->dataCount(synSeq + 1) >= 1 && peer->dataCount(synSeq + 2) >= 1; },
                                  2000));
    }

    // Both outstanding frames must be retransmitted at least once.
    void expectRetransmitted() {
        CHECK(
            rogue_test::waitUntil([&] { return peer->dataCount(synSeq + 1) >= 2 && peer->dataCount(synSeq + 2) >= 2; },
                                  2000));
        CHECK(client->getOpen());
        CHECK_EQ(client->getDropCount(), 0);
        CHECK_GE(client->getRetranCount(), 2);
    }

    // A valid cumulative ack releases both frames: retransmission stops.
    void expectReleasedByValidAck() {
        injectAck(client->transport(), pool, synSeq + 2);
        // Let any retransmission already in flight land, then require silence.
        sleepMs(100);
        uint32_t first  = peer->dataCount(synSeq + 1);
        uint32_t second = peer->dataCount(synSeq + 2);
        sleepMs(200);
        CHECK_EQ(peer->dataCount(synSeq + 1), first);
        CHECK_EQ(peer->dataCount(synSeq + 2), second);
        CHECK(client->getOpen());
    }
};

}  // namespace

TEST_CASE("rpr::Controller ignores a stale ack behind the transmit window") {
    Fixture fx;
    fx.sendTwo();

    // lastAckRx_ is synSeq; an ack one behind it used to walk all 255 slots.
    injectAck(fx.client->transport(), fx.pool, fx.synSeq - 1);

    fx.expectRetransmitted();
    fx.expectReleasedByValidAck();
}

TEST_CASE("rpr::Controller ignores an ack for a sequence not yet sent") {
    Fixture fx;
    fx.sendTwo();

    // locSequence_ is synSeq + 3: the next sequence to be assigned, not outstanding.
    injectAck(fx.client->transport(), fx.pool, fx.synSeq + 3);

    fx.expectRetransmitted();
    fx.expectReleasedByValidAck();
}

TEST_CASE("rpr::Controller accepts a partial ack inside the transmit window") {
    Fixture fx;
    fx.sendTwo();

    injectAck(fx.client->transport(), fx.pool, fx.synSeq + 1);
    sleepMs(50);
    uint32_t first = fx.peer->dataCount(fx.synSeq + 1);

    // Only the second frame is still outstanding.
    CHECK(rogue_test::waitUntil([&] { return fx.peer->dataCount(fx.synSeq + 2) >= 2; }, 2000));
    CHECK_EQ(fx.peer->dataCount(fx.synSeq + 1), first);
    CHECK_EQ(fx.client->getDropCount(), 0);

    fx.expectReleasedByValidAck();
}
