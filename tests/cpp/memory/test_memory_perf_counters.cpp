/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Behavioural coverage for the transaction-path performance counters: the
 * process-wide Transaction construction count (covering both the create()
 * factory and the createSubTransaction() path that bypasses it), and the
 * transaction request count/byte total at Master::intTransaction, the single
 * chokepoint both reqTransaction and reqTransactionPy funnel through.
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
#include <sys/time.h>

#include <memory>
#include <vector>

#include "doctest/doctest.h"
#include "rogue/PerfCounters.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Master.h"
#include "rogue/interfaces/memory/Slave.h"
#include "rogue/interfaces/memory/Transaction.h"

namespace rim = rogue::interfaces::memory;

namespace {

// A Slave that completes every transaction immediately, so
// Master::reqTransaction() (and therefore intTransaction()) returns
// synchronously without a background thread or real transport.
class ImmediateSlave : public rim::Slave {
  public:
    ImmediateSlave() : rim::Slave(1, 0xFFFFFFFF) {}

    void doTransaction(rim::TransactionPtr transaction) override {
        auto lock = transaction->lock();
        transaction->done();
    }
};

}  // namespace

TEST_CASE("Master::reqTransaction raises the process-wide transaction construction count by exactly one") {
    auto master = rim::Master::create();
    auto slave  = std::make_shared<ImmediateSlave>();
    master->setSlave(slave);

    uint8_t data[4] = {0, 0, 0, 0};

    uint64_t before = rogue::PerfCounters::getTransactionCreateCount();
    master->reqTransaction(0x0, sizeof(data), data, rim::Write);
    CHECK_EQ(rogue::PerfCounters::getTransactionCreateCount() - before, 1U);

    master->reqTransaction(0x0, sizeof(data), data, rim::Write);
    CHECK_EQ(rogue::PerfCounters::getTransactionCreateCount() - before, 2U);
}

TEST_CASE(
    "Transaction::createSubTransaction also raises the process-wide construction count by exactly one, "
    "since it bypasses Transaction::create() entirely") {
    struct timeval timeout = {1, 0};
    auto parentTran         = std::make_shared<rim::Transaction>(timeout);

    // Measure the delta starting *after* the parent construction above, so
    // this case isolates createSubTransaction()'s own contribution. If the
    // counter had been placed in the create() factory instead of the
    // constructor, this delta would be zero rather than one, since
    // createSubTransaction() calls std::make_shared<rim::Transaction>
    // directly and never routes through create().
    uint64_t before = rogue::PerfCounters::getTransactionCreateCount();

    auto subTran = parentTran->createSubTransaction();
    CHECK_EQ(rogue::PerfCounters::getTransactionCreateCount() - before, 1U);
}

TEST_CASE(
    "Master::reqTransaction raises the transaction request count by exactly one and the request byte total "
    "by exactly the transaction size") {
    auto master = rim::Master::create();
    auto slave  = std::make_shared<ImmediateSlave>();
    master->setSlave(slave);

    uint8_t data[16] = {0};

    uint64_t countBefore = rogue::PerfCounters::getTransactionRequestCount();
    uint64_t bytesBefore = rogue::PerfCounters::getTransactionRequestBytes();

    master->reqTransaction(0x0, sizeof(data), data, rim::Write);

    CHECK_EQ(rogue::PerfCounters::getTransactionRequestCount() - countBefore, 1U);
    CHECK_EQ(rogue::PerfCounters::getTransactionRequestBytes() - bytesBefore, sizeof(data));

    master->reqTransaction(0x0, 4, data, rim::Read);

    CHECK_EQ(rogue::PerfCounters::getTransactionRequestCount() - countBefore, 2U);
    CHECK_EQ(rogue::PerfCounters::getTransactionRequestBytes() - bytesBefore, sizeof(data) + 4U);
}
