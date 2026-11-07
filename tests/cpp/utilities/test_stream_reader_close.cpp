/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Regression test for StreamReader teardown while the read thread is active.
 * close() and the destructor used to join the read thread while holding
 * mtx_, which the read thread takes on file rollover and on exit, so any
 * close before EOF deadlocked. The destructor must return promptly instead.
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
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <future>
#include <memory>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "doctest/doctest.h"

#include "rogue/interfaces/stream/Frame.h"
#include "rogue/interfaces/stream/Slave.h"
#include "rogue/utilities/fileio/StreamReader.h"

namespace ris = rogue::interfaces::stream;
namespace ruf = rogue::utilities::fileio;

namespace {

constexpr uint32_t FrameCount = 4096;
constexpr uint32_t FrameSize  = 1024;

class SlowSink : public ris::Slave {
  public:
    SlowSink() : ris::Slave() {}

    void acceptFrame(ris::FramePtr frame) override {
        count.fetch_add(1);
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }

    std::atomic<uint32_t> count{0};
};

// ~4 MB of records; at 5 ms per frame the reader needs ~20 s to reach EOF.
std::string writeDataFile() {
    char path[] = "/tmp/rogue_stream_reader_close_XXXXXX.dat";
    int fd      = mkstemps(path, 4);
    REQUIRE(fd >= 0);

    std::vector<uint8_t> record(8 + FrameSize, 0);
    const uint32_t size = FrameSize + 4;
    const uint32_t meta = 0;
    memcpy(record.data(), &size, 4);
    memcpy(record.data() + 4, &meta, 4);

    for (uint32_t i = 0; i < FrameCount; ++i)
        REQUIRE(write(fd, record.data(), record.size()) == static_cast<ssize_t>(record.size()));
    ::close(fd);
    return path;
}

}  // namespace

TEST_CASE("StreamReader destructor returns while the read thread is active") {
    const std::string path = writeDataFile();

    auto sink   = std::make_shared<SlowSink>();
    auto reader = std::make_shared<ruf::StreamReader>();
    reader->addSlave(sink);
    reader->open(path);

    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    while (sink->count.load() == 0 && std::chrono::steady_clock::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    REQUIRE(sink->count.load() > 0);
    REQUIRE(reader->isActive());

    // Drop the last reference on a separate thread so a deadlock shows up as
    // a timeout rather than a hung test binary.
    std::promise<void> done;
    std::future<void> fut = done.get_future();
    std::thread([r = std::move(reader), &done]() mutable {
        r.reset();
        done.set_value();
    }).detach();

    const bool returned = fut.wait_for(std::chrono::seconds(5)) == std::future_status::ready;
    unlink(path.c_str());
    if (!returned) {
        // The detached thread is stuck holding references; skip normal teardown.
        fprintf(stderr, "FAIL: StreamReader destructor deadlocked against an active reader\n");
        _exit(1);
    }
    CHECK(sink->count.load() < FrameCount);
}
