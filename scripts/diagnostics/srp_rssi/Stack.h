/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description :
 *    Hardware-free SRP / RSSI burst diagnostic
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
#ifndef SRP_RSSI_STACK_H
#define SRP_RSSI_STACK_H
#include "Trace.h"
#include <algorithm>
#include <condition_variable>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <vector>
#include "rogue/Logging.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/memory/Hub.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameIterator.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/rssi/Client.h"
#include "rogue/protocols/rssi/Server.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Transport.h"
#include "rogue/protocols/rssi/Header.h"
#include "rogue/protocols/packetizer/CoreV2.h"
#include "rogue/protocols/packetizer/Application.h"
#include "rogue/protocols/packetizer/Transport.h"
#include "rogue/protocols/srp/SrpV3.h"
#include "rogue/protocols/srp/SrpV3Emulation.h"
#include "rogue/protocols/udp/Client.h"
#include "rogue/protocols/udp/Server.h"
namespace ris = rogue::interfaces::stream;
namespace rim = rogue::interfaces::memory;
namespace rpr = rogue::protocols::rssi;
// Copy at the datagram boundary: RSSI retains originals for retransmission;
// its receiver and packetizer destructively consume frame headers/buffers.
class Wire : public ris::Master, public ris::Slave {
    std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<ris::FramePtr> queue_;
    bool run_ = true;
    std::thread worker_;
    bool peer_;
    uint8_t lastAck_ = 0;
    uint64_t freezeEnd_ = 0;

 public:
    explicit Wire(bool peer) : peer_(peer) {
        worker_ = std::thread([this] {
            while (true) {
                ris::FramePtr frame;
                {
                    std::unique_lock<std::mutex> lock(mutex_);
                    cv_.wait(lock, [this] { return !run_ || !queue_.empty(); });
                    if (!run_) return;
                    frame = queue_.front(); queue_.pop_front();
                }
                burst::emit("wire_arrival", this, frame->getPayload(), peer_);
                sendFrame(frame);
            }
        });
    }
    void acceptFrame(ris::FramePtr frame) override {
        auto lock = frame->lock();
        auto copy = ris::Slave::acceptReq(frame->getPayload(), false);
        copy->setPayload(frame->getPayload());
        auto src = frame->begin(), dst = copy->begin();
        ris::copyFrame(src, frame->getPayload(), dst);
        lock.reset();
        // Script a peer that keeps sending valid packets but freezes its ACK
        // and clears BUSY. Recompute the real RSSI header checksum.
        if (peer_) {
            std::lock_guard<std::mutex> guard(mutex_);
            auto h = rpr::Header::create(copy);
            if (h->verify()) {
                if (burst::mode == "ack" && burst::armed.exchange(false)) {
                    freezeEnd_ = burst::now()+static_cast<uint64_t>(burst::delayMs)*1000000;
                    burst::emit("ack_freeze_begin", this, lastAck_);
                }
                if (freezeEnd_ && burst::now() < freezeEnd_) {
                    h->acknowledge = lastAck_; h->busy = false; h->update();
                    burst::emit("ack_frozen", this, lastAck_, h->sequence);
                } else {
                    if (freezeEnd_) burst::emit("ack_freeze_end", this);
                    freezeEnd_ = 0; lastAck_ = h->acknowledge;
                }
            }
            queue_.push_back(copy);
        } else {
            std::lock_guard<std::mutex> guard(mutex_);
            queue_.push_back(copy);
        }
        cv_.notify_one();
    }
    void stop() override {
        { std::lock_guard<std::mutex> guard(mutex_); run_ = false; }
        cv_.notify_all();
        if (worker_.joinable()) worker_.join();
    }
    ~Wire() { stop(); }
};

template<class A, class B> void connect(A a, B b) {
    a->addSlave(b); b->addSlave(a);
}

namespace burst {
class Stack {
 public:
    rpr::ClientPtr client;
    rpr::ServerPtr server;
    rogue::protocols::packetizer::CoreV2Ptr cp, sp;
    rogue::protocols::srp::SrpV3Ptr srp;
    rogue::protocols::srp::SrpV3EmulationPtr emu;
    std::shared_ptr<Wire> out, in;
    std::shared_ptr<rogue::protocols::udp::Client> udpClient;
    std::shared_ptr<rogue::protocols::udp::Server> udpServer;
    uint64_t measureStart = 0;
    std::mutex watchdogMutex;
    std::condition_variable watchdogCv;
    bool finished = false;
    bool reportedOpen = false;
    std::thread watchdog;
    std::string tracePath;

    Stack(unsigned segment, unsigned window, unsigned retran, const std::string& transport) {
        enabled = std::getenv("BURST_TRACE_OFF") == nullptr;
        client = rpr::Client::create(segment);
        server = rpr::Server::create(segment);
        client->setLocMaxBuffers(window);
        server->setLocMaxBuffers(window);
        client->setLocRetranTout(retran);
        server->setLocRetranTout(retran);
        cp = rogue::protocols::packetizer::CoreV2::create(true, true, true);
        constructingPeer = true;
        sp = rogue::protocols::packetizer::CoreV2::create(true, true, true);
        constructingPeer = false;
        srp = rogue::protocols::srp::SrpV3::create();
        emu = rogue::protocols::srp::SrpV3Emulation::create();
        out = std::make_shared<Wire>(false);
        in = std::make_shared<Wire>(true);
        if (transport == "udp") {
            udpServer = rogue::protocols::udp::Server::create(0, false);
            udpClient = rogue::protocols::udp::Client::create("127.0.0.1", udpServer->getPort(), false);
            connect(client->transport(), udpClient);
            connect(server->transport(), udpServer);
        } else {
            client->transport()->addSlave(out); out->addSlave(server->transport());
            server->transport()->addSlave(in); in->addSlave(client->transport());
        }
        connect(client->application(), cp->transport());
        connect(server->application(), sp->transport());
        connect(cp->application(0), srp);
        connect(sp->application(0), emu);
        appTarget = client->application().get();
        txTarget = client->application().get();
        srpTarget = srp.get();
        emit("host_app", appTarget);
        emit("host_srp", srpTarget);
        emit("host_packet_app", cp->application(0).get());
        emit("transport_config", nullptr, segment, window, retran);
    }
    void start() { server->start(); client->start(); }
    bool open() {
        const bool ready = client->getOpen() && server->getOpen();
        if (ready && !reportedOpen) {
            emit("negotiated_host", client.get(), client->curMaxSegment(), client->curMaxBuffers());
            emit("negotiated_peer", server.get(), server->curMaxSegment(), server->curMaxBuffers());
            reportedOpen = true;
        }
        return ready;
    }
    void stop() {
        client->stop(); server->stop(); out->stop(); in->stop();
    }
    void begin(unsigned window, unsigned size, unsigned count, const std::string& path) {
        tracePath = path;
        measureStart = now();
        emit("measure_begin", nullptr, window, size, count);
        watchdog = std::thread([this] {
            std::unique_lock<std::mutex> lock(watchdogMutex);
            if (!watchdogCv.wait_for(lock, std::chrono::seconds(12), [this]{ return finished; })) {
                emit("watchdog", nullptr);
                dump(tracePath);
                std::cerr << "watchdog: Python block workload stopped making progress; trace saved\n";
                std::_Exit(124);
            }
        });
    }
    std::string finish(unsigned completed, bool ok) {
        auto elapsed = now()-measureStart;
        emit("measure_end", nullptr, completed, ok, elapsed);
        std::ostringstream result;
        result << "{\"ok\":" << (ok ? "true" : "false") << ",\"completed\":" << completed
               << ",\"elapsed_ms\":" << elapsed/1e6 << ",\"retransmits\":"
               << client->getRetranCount()+server->getRetranCount() << ",\"resets\":"
               << client->getDownCount()+server->getDownCount() << ",\"events\":" << next.load()
               << ",\"trace_overflow\":" << (next.load() > capacity ? "true" : "false") << "}";
        dump(tracePath);
        { std::lock_guard<std::mutex> lock(watchdogMutex); finished = true; }
        watchdogCv.notify_one();
        if (watchdog.joinable()) watchdog.join();
        return result.str();
    }
    rogue::protocols::srp::SrpV3Ptr memory() { return srp; }
};
}  // namespace burst
#endif
