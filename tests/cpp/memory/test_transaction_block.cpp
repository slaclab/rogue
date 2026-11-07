/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ tests for memory block transaction behavior, including write,
 * read, and verify sequencing, minimum-access expansion to the downstream
 * slave contract, propagation of verify mismatches as block-level errors,
 * expiry of hub sub-transactions once their parent has completed, and Hub
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
#include <cstring>
#include <memory>
#include <string>
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
