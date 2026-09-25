/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * SRP progress through asynchronous RSSI and PacketizerV2 transport.
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

#include <algorithm>
#include <array>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <exception>
#include <future>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Master.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/packetizer/Application.h"
#include "rogue/protocols/packetizer/ControllerV2.h"
#include "rogue/protocols/packetizer/Transport.h"
#include "rogue/protocols/rssi/Application.h"
#include "rogue/protocols/rssi/Controller.h"
#include "rogue/protocols/rssi/Transport.h"
#include "rogue/protocols/srp/SrpV3.h"
#include "rogue/protocols/srp/SrpV3Emulation.h"
#include "support/test_helpers.h"

namespace rim = rogue::interfaces::memory;
namespace ris = rogue::interfaces::stream;
namespace rpp = rogue::protocols::packetizer;
namespace rpr = rogue::protocols::rssi;
namespace rps = rogue::protocols::srp;

namespace {

// Preserve frame allocation/reservations while avoiding ownership cycles in
// bidirectional stream connections. Gates block only when explicitly armed.
class Forwarder : public ris::Slave {
  public:
    explicit Forwarder(const ris::SlavePtr& target) : target_(target) {}

    ris::FramePtr acceptReq(uint32_t size, bool zeroCopy) override {
        auto target = target_.lock();
        return target ? target->acceptReq(size, zeroCopy) : ris::Slave::acceptReq(size, zeroCopy);
    }

    void acceptFrame(ris::FramePtr frame) override {
        {
            std::unique_lock<std::mutex> lock(mutex_);
            if (armed_) {
                entered_ = true;
                ready_.notify_all();
                ready_.wait(lock, [this] { return !armed_; });
            }
        }
        if (auto target = target_.lock()) target->acceptFrame(frame);
    }

    void arm() {
        std::lock_guard<std::mutex> lock(mutex_);
        entered_ = false;
        armed_ = true;
    }

    bool waitForEntry() {
        std::unique_lock<std::mutex> lock(mutex_);
        return ready_.wait_for(lock, std::chrono::seconds(3), [this] { return entered_; });
    }

    void release() {
        std::lock_guard<std::mutex> lock(mutex_);
        armed_ = false;
        ready_.notify_all();
    }

  private:
    std::weak_ptr<ris::Slave> target_;
    std::mutex mutex_;
    std::condition_variable ready_;
    bool armed_ = false;
    bool entered_ = false;
};

std::shared_ptr<Forwarder> connect(const ris::MasterPtr& source, const ris::SlavePtr& target) {
    auto link = std::make_shared<Forwarder>(target);
    source->addSlave(link);
    return link;
}

// Copy each datagram: RSSI retains its transmit frame for retransmission,
// whereas the receiving protocol stack consumes headers and buffer ownership.
// A worker per direction preserves the boundary provided by physical UDP.
class DatagramLink : public ris::Slave {
  public:
    explicit DatagramLink(const ris::SlavePtr& target) : target_(target), worker_([this] { run(); }) {}
    ~DatagramLink() { stop(); }

    void acceptFrame(ris::FramePtr frame) override {
        auto frameLock = frame->lock();
        auto copy = rogue_test::makeFrame(pool_, rogue_test::readFrame(frame, frame->getPayload()));
        frameLock.reset();
        std::lock_guard<std::mutex> lock(mutex_);
        if (running_) queue_.push_back(copy);
        ready_.notify_one();
    }

    void stop() override {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            running_ = false;
        }
        ready_.notify_all();
        if (worker_.joinable()) worker_.join();
    }

    void check() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (failure_) std::rethrow_exception(failure_);
    }

  private:
    void run() {
        try {
            while (true) {
                ris::FramePtr frame;
                {
                    std::unique_lock<std::mutex> lock(mutex_);
                    ready_.wait(lock, [this] { return !running_ || !queue_.empty(); });
                    if (!running_) return;
                    frame = queue_.front();
                    queue_.pop_front();
                }
                if (auto target = target_.lock()) target->acceptFrame(frame);
            }
        } catch (...) {
            std::lock_guard<std::mutex> lock(mutex_);
            failure_ = std::current_exception();
            running_ = false;
        }
    }

    std::weak_ptr<ris::Slave> target_;
    std::shared_ptr<ris::Pool> pool_ = rogue_test::makePool();
    std::mutex mutex_;
    std::condition_variable ready_;
    std::deque<ris::FramePtr> queue_;
    bool running_ = true;
    std::exception_ptr failure_;
    std::thread worker_;
};

// Construct the same controllers/endpoints as Client/Server and CoreV2, but
// let this fixture own the endpoints. Borrowed back-references avoid the
// wrappers' internal shared_ptr cycles, so every worker is joined on teardown.
// Controllers outlive endpoint destructors; these pointers never escape here.
template <class T>
std::shared_ptr<T> borrowed(const std::shared_ptr<T>& object) {
    return std::shared_ptr<T>(object.get(), [](T*) {});
}

struct RssiEndpoint {
    rpr::ControllerPtr controller;
    rpr::TransportPtr transport = rpr::Transport::create();
    rpr::ApplicationPtr application = rpr::Application::create();

    explicit RssiEndpoint(bool server) {
        controller = rpr::Controller::create(1024, borrowed(transport), borrowed(application), server);
        controller->setLocMaxBuffers(8);
        // Generous retransmission timing tolerates CI scheduling; this test
        // asserts completion and data integrity, not deployment timing.
        controller->setLocRetranTout(1000);
        application->setController(controller);
        transport->setController(controller);
    }

    ~RssiEndpoint() { controller->stop(); }
};

struct PacketizerEndpoint {
    rpp::ControllerV2Ptr controller;
    std::array<rpp::ApplicationPtr, 256> applications{};
    rpp::TransportPtr transport = rpp::Transport::create();

    PacketizerEndpoint() {
        controller = rpp::ControllerV2::create(true, true, true, borrowed(transport), applications.data());
        applications[0] = rpp::Application::create(0);
        transport->setController(controller);
        applications[0]->setController(controller);
    }
};

struct Stack {
    RssiEndpoint host{false}, peer{true};
    PacketizerEndpoint hostPacketizer, peerPacketizer;
    rps::SrpV3Ptr srp = rps::SrpV3::create();
    rps::SrpV3EmulationPtr emulator = rps::SrpV3Emulation::create();
    std::shared_ptr<DatagramLink> outbound = std::make_shared<DatagramLink>(peer.transport);
    std::shared_ptr<DatagramLink> inbound = std::make_shared<DatagramLink>(host.transport);
    std::shared_ptr<Forwarder> requests, responses;

    Stack() {
        host.transport->addSlave(outbound);
        peer.transport->addSlave(inbound);
        connect(host.application, hostPacketizer.transport);
        connect(hostPacketizer.transport, host.application);
        connect(peer.application, peerPacketizer.transport);
        connect(peerPacketizer.transport, peer.application);
        requests = connect(srp, hostPacketizer.applications[0]);
        connect(hostPacketizer.applications[0], srp);
        responses = connect(emulator, peerPacketizer.applications[0]);
        connect(peerPacketizer.applications[0], emulator);
    }

    ~Stack() {
        release();
        emulator->stop();
        host.controller->stop();
        peer.controller->stop();
        outbound->stop();
        inbound->stop();
        // Stop RSSI receive workers before destroying packetizer application
        // arrays, which the packetizer controllers reference directly.
        host.application.reset();
        peer.application.reset();
    }

    void release() {
        requests->release();
        responses->release();
    }

    void start() {
        peer.controller->start();
        host.controller->start();
        REQUIRE(rogue_test::waitUntil([this] {
            return host.controller->getOpen() && peer.controller->getOpen();
        }, 5000));
        CHECK_EQ(host.controller->curMaxSegment(), 1024);
        CHECK_EQ(peer.controller->curMaxSegment(), 1024);
        CHECK_EQ(host.controller->curMaxBuffers(), 8);
        CHECK_EQ(peer.controller->curMaxBuffers(), 8);
    }
};

struct ReleaseStack {
    Stack& stack;
    ~ReleaseStack() { stack.release(); }
};

std::vector<uint8_t> page(size_t index, size_t size) {
    std::vector<uint8_t> bytes(size);
    for (size_t i = 0; i < size; ++i) bytes[i] = static_cast<uint8_t>(index * 17 + i * 7 + (i >> 8));
    return bytes;
}

}  // namespace

TEST_CASE("RSSI PacketizerV2 SRP reads complete sequentially and in batches") {
    // Buffers outlive the stack, including when an assertion aborts a batch
    // while other responses are still in flight.
    std::vector<std::vector<uint8_t>> data(24);
    Stack stack;
    auto master = rim::Master::create();
    master->setSlave(stack.srp);
    master->setTimeout(10000000);
    stack.start();

    // Includes single-segment and segmented responses, with a batch larger
    // than the negotiated eight-segment RSSI window.
    for (const size_t size : {4, 4096}) {
        CAPTURE(size);
        for (size_t i = 0; i < 24; ++i) {
            data[i] = page(i, size);
            const auto id = master->reqTransaction(i * 4096, size, data[i].data(), rim::Write);
            master->waitTransaction(id);
            REQUIRE(master->getError().empty());
        }
        for (const size_t outstanding : {1, 24}) {
            CAPTURE(outstanding);
            for (auto& bytes : data) std::fill(bytes.begin(), bytes.end(), 0);
            for (size_t base = 0; base < data.size(); base += outstanding) {
                std::vector<uint32_t> ids;
                for (size_t i = base; i < base + outstanding; ++i)
                    ids.push_back(master->reqTransaction(i * 4096, size, data[i].data(), rim::Read));
                for (size_t j = 0; j < ids.size(); ++j) {
                    master->waitTransaction(ids[j]);
                    REQUIRE(master->getError().empty());
                    CHECK(data[base + j] == page(base + j, size));
                }
            }
        }
    }
    stack.outbound->check();
    stack.inbound->check();
}

TEST_CASE("RSSI PacketizerV2 response completes while a later SRP send is blocked") {
    auto a = page(0, 4096), b = page(1, 4096);
    Stack stack;
    auto first = rim::Master::create();
    auto second = rim::Master::create();
    first->setSlave(stack.srp);
    second->setSlave(stack.srp);
    first->setTimeout(10000000);
    second->setTimeout(10000000);
    stack.start();

    for (size_t i = 0; i < 2; ++i) {
        auto& data = i == 0 ? a : b;
        const auto id = first->reqTransaction(i * 4096, data.size(), data.data(), rim::Write);
        first->waitTransaction(id);
        REQUIRE(first->getError().empty());
    }
    std::fill(a.begin(), a.end(), 0);
    std::fill(b.begin(), b.end(), 0);

    // Guard must unwind before the futures, whose destructors join workers.
    std::future<uint32_t> sender;
    std::future<void> completion;
    ReleaseStack release{stack};
    stack.responses->arm();
    const auto firstId = first->reqTransaction(0, a.size(), a.data(), rim::Read);
    REQUIRE(stack.responses->waitForEntry());
    stack.requests->arm();
    sender = std::async(std::launch::async, [&] {
        return second->reqTransaction(4096, b.size(), b.data(), rim::Read);
    });
    REQUIRE(stack.requests->waitForEntry());
    completion = std::async(std::launch::async, [&] { first->waitTransaction(firstId); });
    stack.responses->release();
    const bool progressed = completion.wait_for(std::chrono::seconds(3)) == std::future_status::ready;
    stack.requests->release();
    const auto secondId = sender.get();
    completion.get();
    second->waitTransaction(secondId);
    CHECK(progressed);
    CHECK(first->getError().empty());
    CHECK(second->getError().empty());
    CHECK(a == page(0, a.size()));
    CHECK(b == page(1, b.size()));
    stack.outbound->check();
    stack.inbound->check();
}
