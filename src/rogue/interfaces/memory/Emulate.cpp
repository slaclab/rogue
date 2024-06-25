/**
 *-----------------------------------------------------------------------------
 * Title      : Memory slave emulator
 * ----------------------------------------------------------------------------
 * File       : Emulator.pp
 * ----------------------------------------------------------------------------
 * Description:
 * A memory space emulator. Allows user to test a Rogue tree without real hardware.
 * This block will auto allocate memory as needed.
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

#include "rogue/Directives.h"

#include "rogue/interfaces/memory/Emulate.h"

#include <inttypes.h>
#include <string.h>

#include <memory>

#include "rogue/GilRelease.h"
#include "rogue/interfaces/memory/Constants.h"
#include "rogue/interfaces/memory/Transaction.h"
#include "rogue/interfaces/memory/TransactionLock.h"

namespace rim = rogue::interfaces::memory;

#ifndef NO_PYTHON
    #include <boost/python.hpp>
namespace bp = boost::python;
#endif

//! Create a block, class creator
rim::EmulatePtr rim::Emulate::create(uint32_t min, uint32_t max) {
    rim::EmulatePtr b = std::make_shared<rim::Emulate>(min, max);
    return (b);
}

//! Create an block
rim::Emulate::Emulate(uint32_t min, uint32_t max) : Slave(min, max) {
   totAlloc_ = 0;
   totSize_ = 0;
   log_ = rogue::Logging::create("memory.Emulate");
}

//! Destroy a block
rim::Emulate::~Emulate() {
    MAP_TYPE::iterator it = memMap_.begin();
    while (it != memMap_.end()) {
        free(it->second);
        ++it;
    }
}

//! Post a transaction. Master will call this method with the access attributes.
void rim::Emulate::doTransaction(rim::TransactionPtr tran) {
    uint64_t addr4k;
    uint64_t off4k;
    uint64_t size4k;
    uint32_t size = tran->size();
    uint32_t type = tran->type();
    uint64_t addr = tran->address();
    uint8_t* ptr  = tran->begin();

    // printf("Got transaction address=0x%" PRIx64 ", size=%" PRIu32 ", type = %" PRIu32 "\n", addr, size, type);

    rogue::interfaces::memory::TransactionLockPtr tlock = tran->lock();
    {
        std::lock_guard<std::mutex> lock(mtx_);

        while (size > 0) {
            addr4k = (addr / 0x1000) * 0x1000;
            off4k  = addr % 0x1000;
            size4k = (addr4k + 0x1000) - (addr4k + off4k);

            if (size4k > size) size4k = size;
            size -= size4k;
            addr += size4k;

            if (memMap_.find(addr4k) == memMap_.end()) {
               memMap_.insert(std::make_pair(addr4k, (uint8_t*)malloc(0x1000)));
               totSize_ += 0x1000;
               totAlloc_ ++;
               log_->debug("Allocating block at 0x%x. Total Blocks %i, Total Size = %i", addr4k, totAlloc_, totSize_);
            }

            // Write or post
            if (tran->type() == rogue::interfaces::memory::Write || tran->type() == rogue::interfaces::memory::Post) {
                // printf("Write data to 4k=0x%" PRIx64 ", offset=0x%" PRIx64 ", size=%" PRIu64 "\n", addr4k, off4k,
                // size4k);
                memcpy(memMap_[addr4k] + off4k, ptr, size4k);
            }

            // Read or verify
            else {
                // printf("Read data from 4k=0x%" PRIx64 ", offset=0x%" PRIx64 ", size=%" PRIu64 "\n", addr4k, off4k,
                // size4k);
                memcpy(ptr, memMap_[addr4k] + off4k, size4k);
            }

            ptr += size4k;
        }
    }
    tran->done();
}

void rim::Emulate::setup_python() {
#ifndef NO_PYTHON
    bp::class_<rim::Emulate, rim::EmulatePtr, bp::bases<rim::Slave>, boost::noncopyable>(
        "Emulate",
        bp::init<uint32_t, uint32_t>());
    bp::implicitly_convertible<rim::EmulatePtr, rim::SlavePtr>();
#endif
}
