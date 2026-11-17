/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression: frames leave rpr::Controller in header order. transportTx() and
 * retransmit() stamp the sequence and acknowledge fields under txMtx_, so a
 * frame whose header was stamped later must not reach the transport slave
 * before a frame whose header was stamped earlier. When it does, the
 * acknowledge numbers on the wire step backwards, which the peer sees as a
 * stale or out of window acknowledgement.
 *
 * Both RSSI endpoints run in this process over loopback UDP with a recording
 * tap between each transport and its UDP socket. The tap sees frames in the
 * order sendFrame() delivers them, which is the order they reach the socket.
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
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "support/test_helpers.h"

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Client.h"
#include "rogue/protocols/rssi/Header.h"
#include "rogue/protocols/rssi/Server.h"
#include "rogue/protocols/rssi/Transport.h"
#include "rogue/protocols/udp/Client.h"
#include "rogue/protocols/udp/Server.h"
#include "rogue/utilities/Prbs.h"

namespace ris = rogue::interfaces::stream;
namespace rpr = rogue::protocols::rssi;
namespace rpu = rogue::protocols::udp;
namespace ru  = rogue::utilities;

namespace {

// Decoded header of one frame as it passed through the tap.
struct WireRecord {
    bool syn;
    bool ack;
    bool nul;
    bool rst;
    uint8_t sequence;
    uint8_t acknowledge;
    uint32_t payload;

    // Data and NULL frames consume a sequence number; bare acks do not.
    bool numbered() const {
        return nul || payload > static_cast<uint32_t>(rpr::Header::HeaderSize);
    }
};

// Pass-through between an RSSI transport and its UDP socket. Records every
// header in the order sendFrame() delivers it, then forwards the frame. The
// record and the forward happen under one mutex so the recorded order is the
// order the frames reach the socket.
class WireTap : public ris::Slave, public ris::Master {
  public:
    ris::FramePtr acceptReq(uint32_t size, bool zeroCopyEn) override {
        return reqFrame(size, zeroCopyEn);
    }

    void acceptFrame(ris::FramePtr frame) override {
        rpr::HeaderPtr head = rpr::Header::create(frame);
        std::lock_guard<std::mutex> guard(mutex_);
        {
            ris::FrameLockPtr lock = frame->lock();
            if (head->verify()) {
                records_.push_back(WireRecord{head->syn,
                                              head->ack,
                                              head->nul,
                                              head->rst,
                                              head->sequence,
                                              head->acknowledge,
                                              frame->getPayload()});
            } else {
                bad_++;
            }
        }
        sendFrame(frame);
    }

    std::vector<WireRecord> records() {
        std::lock_guard<std::mutex> guard(mutex_);
        return records_;
    }

    uint32_t bad() {
        std::lock_guard<std::mutex> guard(mutex_);
        return bad_;
    }

  private:
    std::mutex mutex_;
    std::vector<WireRecord> records_;
    uint32_t bad_ = 0;
};

// One frame whose acknowledge stepped backwards: its index on the wire, the
// highest acknowledge sent before it, and the frame itself.
struct BackwardEvent {
    uint32_t index;
    uint8_t highest;
    WireRecord rec;
};

struct OrderStats {
    uint32_t acked       = 0;  // frames carrying an acknowledge after the handshake
    uint32_t numbered    = 0;  // data and NULL frames after the handshake
    uint32_t backwardAck = 0;  // acknowledge lower than an earlier frame's
    uint32_t backwardSeq = 0;  // sequence lower than an earlier frame's
    std::vector<BackwardEvent> examples;  // first few backward acknowledges
};

// Walk one direction of the wire. Numbering restarts at every SYN or RST, so
// the comparison restarts there too. Deltas are taken modulo 256 and read as
// signed; the outstanding window is far below 128 so a negative delta is a
// frame that was stamped earlier but sent later.
//
// A server transmits acknowledge 0 until its application thread has delivered
// the first frame: stateSendSynAck() never seeds ackSeqRx_ from the client's
// SYN the way stateSendSeqAck() does on the client. The peer's sequence starts
// at 100, so a leading run of zero acknowledges is that placeholder and not a
// real acknowledge; comparison starts at the first non-zero value.
OrderStats analyze(const std::vector<WireRecord>& recs) {
    OrderStats stats;
    bool haveAck    = false;
    bool haveSeq    = false;
    uint8_t lastAck = 0;
    uint8_t lastSeq = 0;

    for (uint32_t i = 0; i < recs.size(); i++) {
        const WireRecord& rec = recs[i];
        if (rec.syn || rec.rst) {
            haveAck = false;
            haveSeq = false;
            continue;
        }

        if (rec.ack && (haveAck || rec.acknowledge != 0)) {
            stats.acked++;
            int8_t delta = static_cast<int8_t>(rec.acknowledge - lastAck);
            if (!haveAck) {
                haveAck = true;
                lastAck = rec.acknowledge;
            } else if (delta < 0) {
                stats.backwardAck++;
                if (stats.examples.size() < 8) stats.examples.push_back(BackwardEvent{i, lastAck, rec});
            } else {
                lastAck = rec.acknowledge;
            }
        }

        if (rec.numbered()) {
            stats.numbered++;
            int8_t delta = static_cast<int8_t>(rec.sequence - lastSeq);
            if (!haveSeq) {
                haveSeq = true;
                lastSeq = rec.sequence;
            } else if (delta < 0) {
                stats.backwardSeq++;
            } else if (delta > 0) {
                lastSeq = rec.sequence;
            }
        }
    }
    return stats;
}

std::string describe(const OrderStats& stats) {
    std::ostringstream out;
    for (const BackwardEvent& ev : stats.examples) {
        out << " [#" << ev.index << " highest=" << static_cast<uint32_t>(ev.highest)
            << " ack=" << static_cast<uint32_t>(ev.rec.acknowledge)
            << " delta=" << static_cast<int32_t>(static_cast<int8_t>(ev.rec.acknowledge - ev.highest))
            << " seq=" << static_cast<uint32_t>(ev.rec.sequence)
            << (ev.rec.nul ? " nul" : "") << (ev.rec.numbered() ? " data" : " bare") << " len=" << ev.rec.payload << "]";
    }
    return out.str();
}

// RSSI client and server connected over loopback UDP with a tap on each
// transmit path and PRBS generators and checkers on both application sides.
struct Duplex {
    rpu::ServerPtr udpSrv;
    rpu::ClientPtr udpCli;
    rpr::ServerPtr rssiSrv;
    rpr::ClientPtr rssiCli;
    std::shared_ptr<WireTap> tapCli;  // client to server direction
    std::shared_ptr<WireTap> tapSrv;  // server to client direction
    ru::PrbsPtr cliTx;
    ru::PrbsPtr cliRx;
    ru::PrbsPtr srvTx;
    ru::PrbsPtr srvRx;

    Duplex()
        : udpSrv(rpu::Server::create(0, false)),
          udpCli(rpu::Client::create("127.0.0.1", static_cast<uint16_t>(udpSrv->getPort()), false)),
          rssiSrv(rpr::Server::create(1400)),
          rssiCli(rpr::Client::create(1400)),
          tapCli(std::make_shared<WireTap>()),
          tapSrv(std::make_shared<WireTap>()),
          cliTx(ru::Prbs::create()),
          cliRx(ru::Prbs::create()),
          srvTx(ru::Prbs::create()),
          srvRx(ru::Prbs::create()) {
        // The default 20 ms retransmit timeout trips on scheduler jitter on a
        // loaded host. Retransmits are legal here but each one repeats an old
        // sequence number, which hides the sequence order check.
        rssiSrv->setLocRetranTout(200);
        rssiCli->setLocRetranTout(200);

        rssiCli->transport()->addSlave(tapCli);
        tapCli->addSlave(udpCli);
        udpCli->addSlave(rssiCli->transport());

        rssiSrv->transport()->addSlave(tapSrv);
        tapSrv->addSlave(udpSrv);
        udpSrv->addSlave(rssiSrv->transport());

        cliTx->addSlave(rssiCli->application());
        rssiCli->application()->addSlave(cliRx);
        cliRx->checkPayload(true);

        srvTx->addSlave(rssiSrv->application());
        rssiSrv->application()->addSlave(srvRx);
        srvRx->checkPayload(true);

        rssiSrv->start();
        rssiCli->start();
        REQUIRE(rogue_test::waitUntil([&] { return rssiCli->getOpen() && rssiSrv->getOpen(); }, 15000));
    }

    ~Duplex() {
        cliTx->disable();
        srvTx->disable();
        rssiCli->stop();
        rssiSrv->stop();
    }
};

}  // namespace

TEST_CASE("rpr::Controller sends frames in header order under full duplex load") {
    // A single pair reorders a handful of frames per 100k on an idle host, so
    // several pairs share the host to raise both the sample count and the
    // scheduler contention that opens the window between stamp and send.
    const uint32_t pairs      = 4;
    const uint32_t frameSize  = 1024;  // one 1400 byte segment per frame, one acknowledge per segment
    const uint32_t loadSecs   = 3;
    const uint32_t minNumbered = 1000;

    std::vector<std::unique_ptr<Duplex>> links;
    for (uint32_t i = 0; i < pairs; i++) links.push_back(std::unique_ptr<Duplex>(new Duplex()));

    for (auto& d : links) {
        d->cliTx->enable(frameSize);
        d->srvTx->enable(frameSize);
    }
    std::this_thread::sleep_for(std::chrono::seconds(loadSecs));
    for (auto& d : links) {
        d->cliTx->disable();
        d->srvTx->disable();
    }

    // Drain so the final acknowledges are on the wire before reading the taps.
    for (auto& d : links) {
        CHECK(rogue_test::waitUntil(
            [&] {
                return d->srvRx->getRxCount() == d->cliTx->getTxCount() &&
                       d->cliRx->getRxCount() == d->srvTx->getTxCount();
            },
            5000));
    }

    uint32_t totalBackwardAck = 0;
    uint32_t totalBackwardSeq = 0;
    uint32_t totalRetran      = 0;

    for (uint32_t i = 0; i < links.size(); i++) {
        Duplex& d      = *links[i];
        OrderStats c2s = analyze(d.tapCli->records());
        OrderStats s2c = analyze(d.tapSrv->records());

        MESSAGE("pair " << i << " client to server: acked=" << c2s.acked << " numbered=" << c2s.numbered
                        << " backward ack=" << c2s.backwardAck << " backward seq=" << c2s.backwardSeq
                        << " retransmits=" << d.rssiCli->getRetranCount() << describe(c2s));
        MESSAGE("pair " << i << " server to client: acked=" << s2c.acked << " numbered=" << s2c.numbered
                        << " backward ack=" << s2c.backwardAck << " backward seq=" << s2c.backwardSeq
                        << " retransmits=" << d.rssiSrv->getRetranCount() << describe(s2c));

        // The order check is only meaningful on a link that stayed up and moved data.
        REQUIRE_EQ(d.rssiCli->getDownCount(), 0U);
        REQUIRE_EQ(d.rssiSrv->getDownCount(), 0U);
        REQUIRE(c2s.numbered > minNumbered);
        REQUIRE(s2c.numbered > minNumbered);
        CHECK_EQ(d.tapCli->bad(), 0U);
        CHECK_EQ(d.tapSrv->bad(), 0U);
        CHECK_EQ(d.cliRx->getRxErrors(), 0U);
        CHECK_EQ(d.srvRx->getRxErrors(), 0U);

        totalBackwardAck += c2s.backwardAck + s2c.backwardAck;
        totalBackwardSeq += c2s.backwardSeq + s2c.backwardSeq;
        totalRetran += d.rssiCli->getRetranCount() + d.rssiSrv->getRetranCount();
    }

    CHECK_EQ(totalBackwardAck, 0U);

    // A retransmit legitimately repeats an older sequence number, so the
    // sequence order check only holds on a run without retransmits.
    if (totalRetran == 0) CHECK_EQ(totalBackwardSeq, 0U);
}
