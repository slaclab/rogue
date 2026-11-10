/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ tests for memory block transaction behavior, including write,
 * read, and verify sequencing, minimum-access expansion to the downstream
 * slave contract, propagation of verify mismatches as block-level errors,
 * expiry of hub sub-transactions once their parent has completed, retention
 * of sub-transaction errors until every child has finished, and Hub
 * forwarding to an unconnected downstream slave.
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
#include <cmath>
#include <cstring>
#include <initializer_list>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/interfaces/memory/Block.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Hub.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/interfaces/memory/Transaction.h"
#include "rogue/interfaces/memory/Variable.h"

namespace rim = rogue::interfaces::memory;

namespace {

struct TransactionRecord {
    uint32_t type;
    uint64_t address;
    uint32_t size;
    std::vector<uint8_t> data;
};

class RecordingMemorySlave : public rim::Slave {
  public:
    explicit RecordingMemorySlave(uint32_t minAccess, std::size_t bytes)
        : rim::Slave(minAccess, static_cast<uint32_t>(bytes)), memory_(bytes, 0), corruptVerify_(false) {}

    void corruptOnNextVerify() {
        corruptVerify_ = true;
    }

    void doTransaction(rim::TransactionPtr transaction) override {
        auto lock = transaction->lock();

        TransactionRecord record = {transaction->type(), transaction->address(), transaction->size(), {}};
        if (transaction->address() + transaction->size() > memory_.size()) {
            transaction->errorStr("transaction out of range");
            return;
        }

        if (transaction->type() == rim::Write || transaction->type() == rim::Post) {
            record.data.assign(transaction->begin(), transaction->end());
            std::copy(record.data.begin(), record.data.end(), memory_.begin() + transaction->address());
            if (corruptVerify_) memory_[transaction->address()] ^= 0xFFU;
        } else if (transaction->type() == rim::Read || transaction->type() == rim::Verify) {
            std::copy(memory_.begin() + transaction->address(),
                      memory_.begin() + transaction->address() + transaction->size(),
                      transaction->begin());
            record.data.assign(transaction->begin(), transaction->end());
            if (transaction->type() == rim::Verify) corruptVerify_ = false;
        }

        records.push_back(record);
        transaction->done();
    }

    std::vector<uint8_t> memory_;
    std::vector<TransactionRecord> records;

  private:
    bool corruptVerify_;
};

// Stashes every transaction it receives and never completes it, modelling a
// link whose responses arrive after the requester has given up.
class StashingMemorySlave : public rim::Slave {
  public:
    explicit StashingMemorySlave(uint32_t maxAccess) : rim::Slave(maxAccess, maxAccess) {}

    void doTransaction(rim::TransactionPtr transaction) override {
        auto lock = transaction->lock();
        stashed.push_back(transaction);
    }

    std::vector<rim::TransactionPtr> stashed;
};

// Completes every transaction inline, failing those that start at one of the
// listed addresses, the way a slave reporting a bad status during Hub
// forwarding does.
class InlineCompletingSlave : public rim::Slave {
  public:
    InlineCompletingSlave(uint32_t maxAccess, std::vector<uint64_t> failAddresses)
        : rim::Slave(maxAccess, maxAccess), failAddresses_(std::move(failAddresses)) {}

    void doTransaction(rim::TransactionPtr transaction) override {
        auto lock = transaction->lock();
        if (std::find(failAddresses_.begin(), failAddresses_.end(), transaction->address()) != failAddresses_.end())
            transaction->errorStr("inline child failure");
        else
            transaction->done();
    }

  private:
    std::vector<uint64_t> failAddresses_;
};

// Issues one read that the Hub splits into kSplitChildren stashed children,
// so a test can complete them in any order and with any outcome.
constexpr uint32_t kSplitMaxAccess = 4;
constexpr uint32_t kSplitChildren  = 3;

struct SplitRead {
    SplitRead()
        : slave(std::make_shared<StashingMemorySlave>(kSplitMaxAccess)),
          hub(rim::Hub::create(0, 0, 0)),
          master(rim::Master::create()),
          buffer(kSplitMaxAccess * kSplitChildren, 0) {
        hub->setSlave(slave);
        master->setSlave(hub);
        master->setTimeout(2000000);  // 2 s
        id = master->reqTransaction(0, static_cast<uint32_t>(buffer.size()), buffer.data(), rim::Read);
        REQUIRE_EQ(slave->stashed.size(), kSplitChildren);
    }

    // Completes child `index`, with an error when `error` is non-empty.
    void finish(std::size_t index, const std::string& error = "") {
        auto& sub = slave->stashed.at(index);
        auto lock = sub->lock();
        if (error.empty())
            sub->done();
        else
            sub->errorStr(error);
    }

    bool childExpired(std::size_t index) {
        auto& sub = slave->stashed.at(index);
        auto lock = sub->lock();
        return sub->expired();
    }

    std::shared_ptr<StashingMemorySlave> slave;
    rim::HubPtr hub;
    rim::MasterPtr master;
    std::vector<uint8_t> buffer;
    uint32_t id;
};

// Keeps the parent transaction alive after the master has released it, the
// way Master::tranMap_ or an in-flight Hub::doTransaction() does in practice.
class ParentHoldingHub : public rim::Hub {
  public:
    ParentHoldingHub() : rim::Hub(0, 0, 0) {}

    void doTransaction(rim::TransactionPtr transaction) override {
        parents.push_back(transaction);
        rim::Hub::doTransaction(transaction);
    }

    std::vector<rim::TransactionPtr> parents;
};

rim::VariablePtr makeUIntVariable(const std::string& name,
                                  uint64_t offset,
                                  uint32_t bitOffset,
                                  uint32_t bitSize,
                                  bool verify = true) {
    auto variable = rim::Variable::create(
        name, "RW", 0, 0, offset, {bitOffset}, {bitSize}, false, verify, false, false, rim::UInt, false, false, 0, 0, 0, 0, 0);
    variable->updatePath("TestBlock." + name);
    return variable;
}

rim::VariablePtr makeFloat8Variable(const std::string& name, uint64_t offset) {
    // Min and max both 0 disables the Block::setFloat8 range check so the
    // encoder itself is exercised with out-of-range inputs.
    auto variable = rim::Variable::create(
        name, "RW", 0, 0, offset, {0}, {8}, false, true, false, false, rim::Float8, false, false, 0, 0, 0, 0, 0);
    variable->updatePath("TestBlock." + name);
    return variable;
}

std::vector<uint8_t> bytesFromUInt32(uint32_t value) {
    std::vector<uint8_t> bytes(sizeof(value));
    std::memcpy(bytes.data(), &value, sizeof(value));
    return bytes;
}

}  // namespace

TEST_CASE("Memory block write and read issue deterministic transactions") {
    auto slave = std::make_shared<RecordingMemorySlave>(1, 1024);
    auto block = rim::Block::create(0x100, 4);
    auto reg   = makeUIntVariable("Reg", 0, 0, 32, true);

    block->setSlave(slave);
    block->addVariables({reg});
    block->setEnable(true);

    uint64_t writeValue = 0x11223344ULL;
    reg->setUInt(writeValue);

    REQUIRE_EQ(slave->records.size(), 2U);
    CHECK_EQ(slave->records[0].type, rim::Write);
    CHECK_EQ(slave->records[0].address, 0x100ULL);
    CHECK_EQ(slave->records[0].size, 4U);
    CHECK_EQ(slave->records[0].data, bytesFromUInt32(static_cast<uint32_t>(writeValue)));
    CHECK_EQ(slave->records[1].type, rim::Verify);
    CHECK_EQ(slave->records[1].data, bytesFromUInt32(static_cast<uint32_t>(writeValue)));

    const uint64_t readValue = reg->getUInt();
    CHECK_EQ(readValue, writeValue);
    REQUIRE_EQ(slave->records.size(), 3U);
    CHECK_EQ(slave->records[2].type, rim::Read);
    CHECK_EQ(slave->records[2].address, 0x100ULL);
    CHECK_EQ(slave->records[2].size, 4U);
}

TEST_CASE("Memory block expands narrow transactions to the slave minimum access size") {
    auto slave = std::make_shared<RecordingMemorySlave>(4, 1024);
    auto block = rim::Block::create(0x200, 4);
    auto reg   = makeUIntVariable("ByteReg", 0, 8, 8, true);

    block->setSlave(slave);
    block->addVariables({reg});
    block->setEnable(true);

    uint64_t writeValue = 0xABU;
    reg->setUInt(writeValue);

    REQUIRE_EQ(slave->records.size(), 2U);
    CHECK_EQ(slave->records[0].type, rim::Write);
    CHECK_EQ(slave->records[0].address, 0x200ULL);
    CHECK_EQ(slave->records[0].size, 4U);
    CHECK_EQ(slave->memory_[0x200], 0x00U);
    CHECK_EQ(slave->memory_[0x201], 0xABU);
    CHECK_EQ(slave->memory_[0x202], 0x00U);
    CHECK_EQ(slave->memory_[0x203], 0x00U);
}

TEST_CASE("Memory block surfaces verify mismatches as transaction errors") {
    auto slave = std::make_shared<RecordingMemorySlave>(1, 1024);
    auto block = rim::Block::create(0x300, 4);
    auto reg   = makeUIntVariable("VerifyReg", 0, 0, 32, true);

    block->setSlave(slave);
    block->addVariables({reg});
    block->setEnable(true);
    slave->corruptOnNextVerify();

    uint64_t writeValue = 0x55667788ULL;
    CHECK_THROWS_AS(reg->setUInt(writeValue), rogue::GeneralError);
    REQUIRE_EQ(slave->records.size(), 2U);
    CHECK_EQ(slave->records[0].type, rim::Write);
    CHECK_EQ(slave->records[1].type, rim::Verify);
}

TEST_CASE("Hub sub-transactions expire once their parent has timed out") {
    constexpr uint32_t kMaxAccess = 4;
    constexpr uint32_t kSize      = 16;
    constexpr uint8_t kFill       = 0xA5U;

    auto slave  = std::make_shared<StashingMemorySlave>(kMaxAccess);
    auto hub    = std::make_shared<ParentHoldingHub>();
    auto master = rim::Master::create();

    hub->setSlave(slave);
    master->setSlave(hub);
    master->setTimeout(1000);

    std::vector<uint8_t> buffer(kSize, kFill);
    const uint32_t id = master->reqTransaction(0, kSize, buffer.data(), rim::Read);
    master->waitTransaction(id);

    CHECK_FALSE(master->getError().empty());
    REQUIRE_EQ(hub->parents.size(), 1U);
    REQUIRE_EQ(slave->stashed.size(), kSize / kMaxAccess);

    // Late responses: a well-behaved slave only writes when not expired.
    for (const auto& sub : slave->stashed) {
        auto lock = sub->lock();
        CHECK(sub->expired());
        if (!sub->expired()) std::memset(sub->begin(), 0x5A, sub->size());
        sub->done();
    }

    CHECK_EQ(buffer, std::vector<uint8_t>(kSize, kFill));
}

TEST_CASE("Memory hub forwards to an unconnected slave instead of splitting by zero max access") {
    // The placeholder slave behind an unwired Hub reports maxAccess 0. The Hub
    // must forward the transaction so the placeholder reports the unconnected
    // bus error, rather than splitting into zero children and timing out.
    auto hub    = rim::Hub::create(0x1000, 0, 0);
    auto master = rim::Master::create();
    master->setSlave(hub);
    master->setTimeout(2000000);  // 2 s

    std::vector<uint8_t> data(4, 0);
    const auto start = std::chrono::steady_clock::now();
    master->reqTransaction(0, static_cast<uint32_t>(data.size()), data.data(), rim::Read);
    master->waitTransaction(0);
    const auto elapsed = std::chrono::steady_clock::now() - start;

    CHECK_NE(master->getError().find("unconnected memory bus"), std::string::npos);
    CHECK_LT(elapsed, std::chrono::seconds(1));
}

TEST_CASE("Split transaction retains an earlier child error until every child completes") {
    SplitRead read;

    read.finish(0, "first child failed");

    // The parent must stay open while other children still use its buffer.
    CHECK_FALSE(read.childExpired(1));
    CHECK_FALSE(read.childExpired(2));

    read.finish(1);
    CHECK_FALSE(read.childExpired(2));

    read.finish(2);
    CHECK(read.childExpired(2));

    read.master->waitTransaction(read.id);
    CHECK_NE(read.master->getError().find("first child failed"), std::string::npos);
}

TEST_CASE("Split transaction reports a later child error after earlier children succeed") {
    SplitRead read;

    read.finish(0);
    read.finish(1);
    read.finish(2, "last child failed");

    read.master->waitTransaction(read.id);
    CHECK_NE(read.master->getError().find("last child failed"), std::string::npos);
}

TEST_CASE("Split transaction reports every failed child") {
    SplitRead read;

    read.finish(0, "first child failed");
    read.finish(1);
    read.finish(2, "last child failed");

    read.master->waitTransaction(read.id);
    const std::string error = read.master->getError();
    CHECK_NE(error.find("first child failed"), std::string::npos);
    CHECK_NE(error.find("last child failed"), std::string::npos);
}

TEST_CASE("Split transaction succeeds when every child succeeds") {
    SplitRead read;

    read.finish(2);
    read.finish(0);
    read.finish(1);

    read.master->waitTransaction(read.id);
    CHECK(read.master->getError().empty());
}

TEST_CASE("Split transaction retains a child error raised while the Hub is still forwarding") {
    constexpr uint32_t kMaxAccess = 4;
    constexpr uint32_t kSize      = 12;

    for (uint64_t failAddress : std::initializer_list<uint64_t>{0, 4, 8}) {
        CAPTURE(failAddress);
        auto slave  = std::make_shared<InlineCompletingSlave>(kMaxAccess, std::vector<uint64_t>{failAddress});
        auto hub    = rim::Hub::create(0, 0, 0);
        auto master = rim::Master::create();
        hub->setSlave(slave);
        master->setSlave(hub);
        master->setTimeout(2000000);  // 2 s

        std::vector<uint8_t> buffer(kSize, 0);
        const uint32_t id = master->reqTransaction(0, kSize, buffer.data(), rim::Read);
        master->waitTransaction(id);

        CHECK_NE(master->getError().find("inline child failure"), std::string::npos);
    }
}

TEST_CASE("Memory block float8 encoder clamps near-overflow values instead of producing NaN") {
    auto slave = std::make_shared<RecordingMemorySlave>(1, 1024);
    auto block = rim::Block::create(0x380, 4);
    auto reg   = makeFloat8Variable("Float8Reg", 0);

    block->setSlave(slave);
    block->addVariables({reg});
    block->setEnable(true);

    // 500.0 rebiases to E4M3 exponent 15 with mantissa 0b111, which is the
    // reserved NaN pattern 0x7F. The encoder must clamp to max finite (0x7E).
    float writeValue = 500.0F;
    reg->setFloat8(writeValue);
    CHECK_EQ(slave->memory_[0x380], 0x7EU);

    const float readValue = reg->getFloat8();
    CHECK_FALSE(std::isnan(readValue));
    CHECK_EQ(readValue, 448.0F);

    float negValue = -511.9F;
    reg->setFloat8(negValue);
    CHECK_EQ(slave->memory_[0x380], 0xFEU);
    CHECK_EQ(reg->getFloat8(), -448.0F);
}
