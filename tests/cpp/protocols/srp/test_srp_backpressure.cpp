/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * SRPv0/SRPv3 transaction progress under transport backpressure and early replies.
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
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <future>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Hub.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/FrameLock.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/protocols/srp/SrpV0.h"
#include "rogue/protocols/srp/SrpV3.h"
#include "support/test_helpers.h"

namespace rim = rogue::interfaces::memory;
namespace ris = rogue::interfaces::stream;
namespace rps = rogue::protocols::srp;

namespace {

uint8_t readValue(uint64_t address) {
    return static_cast<uint8_t>(address * 7 + 0x51);
}

struct Request {
    uint64_t address;
    uint32_t size;
    bool write;
};

struct SrpV0Wire {
    using Srp = rps::SrpV0;
    static constexpr size_t writeHeader = 8;
    static constexpr size_t writeTail = 4;

    static Request decode(const std::vector<uint8_t>& bytes) {
        uint32_t header[3];
        std::memcpy(header, bytes.data(), sizeof(header));
        const bool write = header[1] & 0x40000000;
        const auto size = write ? bytes.size() - writeHeader - writeTail : (header[2] + 1) * 4;
        return {static_cast<uint64_t>(header[1] & 0x3FFFFFFF) << 2, static_cast<uint32_t>(size), write};
    }
};

struct SrpV3Wire {
    using Srp = rps::SrpV3;
    static constexpr size_t writeHeader = 20;
    static constexpr size_t writeTail = 0;

    static Request decode(const std::vector<uint8_t>& bytes) {
        uint32_t header[5];
        std::memcpy(header, bytes.data(), sizeof(header));
        return {(static_cast<uint64_t>(header[3]) << 32) | header[2], header[4] + 1,
                (header[0] & 0x300) == 0x100};
    }
};

// Minimal wire-format peers: echo write data and generate address-dependent
// reads. No transaction internals or production locks are exposed to the test.
template <class Wire>
ris::FramePtr responseFor(const ris::FramePtr& request) {
    auto lock = request->lock();
    auto bytes = rogue_test::readFrame(request, request->getPayload());
    const auto info = Wire::decode(bytes);
    // Both versions echo the write header on responses and append a status word.
    std::vector<uint8_t> response(Wire::writeHeader + info.size + 4, 0);
    std::copy_n(bytes.begin(), Wire::writeHeader, response.begin());
    if (info.write) {
        std::copy_n(bytes.begin() + Wire::writeHeader, info.size, response.begin() + Wire::writeHeader);
    } else {
        for (uint32_t i = 0; i < info.size; ++i) response[Wire::writeHeader + i] = readValue(info.address + i);
    }
    return rogue_test::makeFrame(rogue_test::makePool(), response);
}

class ControlledPeer : public ris::Slave {
  public:
    explicit ControlledPeer(size_t blockedRequest) : blockedRequest_(blockedRequest) {}

    void acceptFrame(ris::FramePtr frame) override {
        std::unique_lock<std::mutex> lock(mutex_);
        requests_.push_back(frame);
        ready_.notify_all();
        if (requests_.size() == blockedRequest_) ready_.wait(lock, [this] { return released_; });
    }

    bool waitForRequests(size_t count) {
        std::unique_lock<std::mutex> lock(mutex_);
        return ready_.wait_for(lock, std::chrono::seconds(3), [this, count] { return requests_.size() >= count; });
    }

    ris::FramePtr request(size_t index) {
        std::lock_guard<std::mutex> lock(mutex_);
        return requests_.at(index);
    }

    void release() {
        std::lock_guard<std::mutex> lock(mutex_);
        released_ = true;
        ready_.notify_all();
    }

  private:
    const size_t blockedRequest_;
    std::mutex mutex_;
    std::condition_variable ready_;
    bool released_ = false;
    std::vector<ris::FramePtr> requests_;
};

template <class Wire>
class InlinePeer : public ris::Slave {
  public:
    InlinePeer(const std::shared_ptr<typename Wire::Srp>& srp, bool reply) : srp_(srp), reply_(reply) {}

    void acceptFrame(ris::FramePtr frame) override {
        auto bytes = rogue_test::readFrame(frame, frame->getPayload());
        const auto info = Wire::decode(bytes);
        sizes.push_back(info.size);
        addresses.push_back(info.address);
        // SRPv0 posted writes have no distinct wire opcode; the fixture knows
        // whether a response is wanted from the requested transaction type.
        if (reply_) srp_.lock()->acceptFrame(responseFor<Wire>(frame));
    }

    std::vector<uint32_t> sizes;
    std::vector<uint64_t> addresses;

  private:
    std::weak_ptr<typename Wire::Srp> srp_;
    const bool reply_;
};

}  // namespace

TEST_CASE_TEMPLATE("SRP completes an earlier response while a later send is blocked", Wire, SrpV0Wire, SrpV3Wire) {
    uint32_t type = rim::Read;
    SUBCASE("read") { type = rim::Read; }
    SUBCASE("write") { type = rim::Write; }
    SUBCASE("verify") { type = rim::Verify; }

    auto srp = Wire::Srp::create();
    auto peer = std::make_shared<ControlledPeer>(2);
    srp->addSlave(peer);
    auto first = rim::Master::create();
    auto second = rim::Master::create();
    first->setSlave(srp);
    second->setSlave(srp);
    first->setTimeout(10000000);
    second->setTimeout(10000000);
    std::vector<uint8_t> a(256, 0xA5), b(256, 0x5A);
    const auto firstId = first->reqTransaction(0, a.size(), a.data(), type);
    auto sender = std::async(std::launch::async, [&] {
        return second->reqTransaction(4096, b.size(), b.data(), type);
    });
    const bool entered = peer->waitForRequests(2);
    if (!entered) {
        peer->release();
        sender.get();
        FAIL("Second request did not reach the controlled transport");
        return;
    }
    auto receiver = std::async(std::launch::async, [&] { srp->acceptFrame(responseFor<Wire>(peer->request(0))); });
    const bool progressed = receiver.wait_for(std::chrono::seconds(3)) == std::future_status::ready;
    // Always release the gate before assertions/joins, including on old code.
    peer->release();
    const auto secondId = sender.get();
    receiver.get();
    CHECK(progressed);
    srp->acceptFrame(responseFor<Wire>(peer->request(1)));
    first->waitTransaction(firstId);
    second->waitTransaction(secondId);
    CHECK(first->getError().empty());
    CHECK(second->getError().empty());
    for (size_t i = 0; i < a.size(); ++i) {
        CHECK_EQ(a[i], type == rim::Write ? 0xA5 : readValue(i));
        CHECK_EQ(b[i], type == rim::Write ? 0x5A : readValue(4096 + i));
    }
}

TEST_CASE_TEMPLATE("SRP posted data survives completion while its send is blocked", Wire, SrpV0Wire, SrpV3Wire) {
    auto srp = Wire::Srp::create();
    auto peer = std::make_shared<ControlledPeer>(1);
    srp->addSlave(peer);
    auto master = rim::Master::create();
    master->setSlave(srp);
    std::vector<uint8_t> data(256, 0xA5);
    auto sender = std::async(std::launch::async, [&] {
        return master->reqTransaction(0, data.size(), data.data(), rim::Post);
    });
    const bool entered = peer->waitForRequests(1);
    if (!entered) {
        peer->release();
        sender.get();
        FAIL("Posted write did not reach the controlled transport");
        return;
    }
    auto completion = std::async(std::launch::async, [&] { master->waitTransaction(0); });
    const bool progressed = completion.wait_for(std::chrono::seconds(3)) == std::future_status::ready;
    if (progressed) std::fill(data.begin(), data.end(), 0);
    auto frame = peer->request(0);
    auto serialized = rogue_test::readFrame(frame, frame->getPayload());
    peer->release();
    sender.get();
    completion.get();
    CHECK(progressed);
    CHECK(master->getError().empty());
    REQUIRE_EQ(serialized.size(), Wire::writeHeader + data.size() + Wire::writeTail);
    CHECK(std::all_of(serialized.begin() + Wire::writeHeader, serialized.end() - Wire::writeTail,
                      [](uint8_t v) { return v == 0xA5; }));
}

TEST_CASE_TEMPLATE("SRP supports inline completion including split Hub children", Wire, SrpV0Wire, SrpV3Wire) {
    uint32_t type = rim::Read;
    SUBCASE("read") { type = rim::Read; }
    SUBCASE("write") { type = rim::Write; }
    SUBCASE("verify") { type = rim::Verify; }
    SUBCASE("post") { type = rim::Post; }

    auto srp = Wire::Srp::create();
    auto peer = std::make_shared<InlinePeer<Wire>>(srp, type != rim::Post);
    srp->addSlave(peer);
    auto hub = rim::Hub::create(0x1000, 0, 0);
    hub->setSlave(srp);
    auto master = rim::Master::create();
    master->setSlave(hub);
    // Three children, including a partial final frame. Every child may finish
    // and remove itself from the parent's pending map before forwarding returns.
    const auto childSize = srp->max();
    std::vector<uint8_t> data(childSize * 2 + 256, 0xA5);
    const auto id = master->reqTransaction(0, data.size(), data.data(), type);
    master->waitTransaction(id);
    CHECK(master->getError().empty());
    CHECK(peer->sizes == std::vector<uint32_t>{childSize, childSize, 256});
    CHECK(peer->addresses == std::vector<uint64_t>{0x1000, 0x1000 + childSize, 0x1000 + 2 * childSize});
    for (size_t i = 0; i < data.size(); ++i)
        CHECK_EQ(data[i], type == rim::Read || type == rim::Verify ? readValue(0x1000 + i) : 0xA5);
}

TEST_CASE_TEMPLATE("SRP ignores late response data after timeout and accepts the next read", Wire, SrpV0Wire, SrpV3Wire) {
    auto srp = Wire::Srp::create();
    auto peer = std::make_shared<ControlledPeer>(0);
    srp->addSlave(peer);
    auto master = rim::Master::create();
    master->setSlave(srp);
    master->setTimeout(1000);
    std::vector<uint8_t> data(256, 0xCC);
    const auto lateId = master->reqTransaction(0, data.size(), data.data(), rim::Read);
    master->waitTransaction(lateId);
    CHECK(master->getError().find("Timeout") != std::string::npos);
    srp->acceptFrame(responseFor<Wire>(peer->request(0)));
    CHECK(std::all_of(data.begin(), data.end(), [](uint8_t v) { return v == 0xCC; }));

    master->clearError();
    master->setTimeout(10000000);
    const auto nextId = master->reqTransaction(0, data.size(), data.data(), rim::Read);
    srp->acceptFrame(responseFor<Wire>(peer->request(1)));
    master->waitTransaction(nextId);
    CHECK(master->getError().empty());
    for (size_t i = 0; i < data.size(); ++i) CHECK_EQ(data[i], readValue(i));
}
