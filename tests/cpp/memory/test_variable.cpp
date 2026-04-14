/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Native C++ tests for memory variable metadata and typed access behavior,
 * including list geometry bookkeeping, offset normalization, dispatch to the
 * correct typed accessors, and indexed list access with stride/range checks.
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
#include <memory>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/interfaces/memory/Block.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/interfaces/memory/Transaction.h"
#include "rogue/interfaces/memory/Variable.h"

namespace rim = rogue::interfaces::memory;

namespace {

class RecordingMemorySlave : public rim::Slave {
  public:
    explicit RecordingMemorySlave(std::size_t bytes) : rim::Slave(1, static_cast<uint32_t>(bytes)), memory_(bytes, 0) {}

    void doTransaction(rim::TransactionPtr transaction) override {
        auto lock = transaction->lock();

        if (transaction->address() + transaction->size() > memory_.size()) {
            transaction->errorStr("transaction out of range");
            return;
        }

        if (transaction->type() == rim::Write || transaction->type() == rim::Post) {
            std::copy(transaction->begin(), transaction->end(), memory_.begin() + transaction->address());
        } else if (transaction->type() == rim::Read || transaction->type() == rim::Verify) {
            std::copy(memory_.begin() + transaction->address(),
                      memory_.begin() + transaction->address() + transaction->size(),
                      transaction->begin());
        }

        transaction->done();
    }

    std::vector<uint8_t> memory_;
};

}  // namespace

TEST_CASE("Memory variable metadata tracks list geometry and path updates") {
    auto variable = rim::Variable::create(
        "List", "RW", 0, 0, 8, {0}, {8}, false, true, false, false, rim::UInt, false, false, 0, 4, 8, 16, 3);

    CHECK_EQ(variable->name(), "List");
    CHECK_EQ(variable->path(), "List");
    variable->updatePath("Root.List");
    CHECK_EQ(variable->path(), "Root.List");
    CHECK_EQ(variable->offset(), 8ULL);
    CHECK_EQ(variable->numValues(), 4U);
    CHECK_EQ(variable->valueBits(), 8U);
    CHECK_EQ(variable->valueBytes(), 1U);
    CHECK_EQ(variable->valueStride(), 16U);
    CHECK_EQ(variable->retryCount(), 3U);
    CHECK_EQ(variable->varBytes(), 7U);
}

TEST_CASE("Memory variable shiftOffsetDown updates offset and transfer coverage") {
    auto variable =
        rim::Variable::create("Packed", "RW", 0, 0, 4, {0, 16}, {8, 8}, false, false, false, false, rim::UInt, false, false, 0, 0, 0, 0, 0);

    CHECK_EQ(variable->offset(), 4ULL);
    CHECK_EQ(variable->varBytes(), 3U);

    variable->shiftOffsetDown(1, 4);

    CHECK_EQ(variable->offset(), 3ULL);
    CHECK_EQ(variable->varBytes(), 4U);
}

TEST_CASE("Memory variable rejects incompatible typed accessors") {
    auto variable =
        rim::Variable::create("Text", "RW", 0, 0, 0, {0}, {32}, false, false, false, false, rim::String, false, false, 0, 0, 0, 0, 0);

    uint64_t writeValue = 7U;
    CHECK_THROWS_AS(variable->setUInt(writeValue), rogue::GeneralError);
    CHECK_THROWS_AS(variable->getUInt(), rogue::GeneralError);
}

TEST_CASE("Memory list variables honor stride and range checks") {
    auto slave = std::make_shared<RecordingMemorySlave>(16);
    auto block = rim::Block::create(0, 8);
    auto variable = rim::Variable::create(
        "List", "RW", 0, 0, 0, {0}, {8}, false, true, false, false, rim::UInt, false, false, 0, 4, 8, 16, 0);

    variable->updatePath("Root.List");
    block->setSlave(slave);
    block->addVariables({variable});
    block->setEnable(true);

    uint64_t first  = 0x11U;
    uint64_t third  = 0x22U;
    uint64_t badIdx = 0x33U;

    variable->setUInt(first, 0);
    variable->setUInt(third, 2);

    CHECK_EQ(slave->memory_[0], 0x11U);
    CHECK_EQ(slave->memory_[2], 0x00U);
    CHECK_EQ(slave->memory_[4], 0x22U);
    CHECK_EQ(variable->getUInt(2), 0x22U);

    CHECK_THROWS_AS(variable->setUInt(badIdx, 4), rogue::GeneralError);
}
