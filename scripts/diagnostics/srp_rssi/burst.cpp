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
#include "Stack.h"
#include <algorithm>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    if (argc != 11) {
        std::cerr << "burst WINDOW BYTES COUNT MODE DELAY_MS TRACE.csv TRANSPORT SPLIT RETRAN_MS WORKERS\n";
        return 2;
    }
    if (const char* after = std::getenv("BURST_STALL_AFTER")) burst::stallAfter = std::stoul(after);
    burst::enabled = std::getenv("BURST_TRACE_OFF") == nullptr;
    const unsigned window = std::stoul(argv[1]), size = std::stoul(argv[2]), count = std::stoul(argv[3]);
    burst::mode = argv[4]; burst::delayMs = std::stoul(argv[5]);
    const std::string trace = argv[6], transport = argv[7];
    const bool split = std::stoi(argv[8]);
    const unsigned workers = std::stoul(argv[10]);
    if (!window || !workers || !count || size < 4 || size > 4096 || size%4) return 2;
    // Watchdog is independent of memory transaction timeout: submission itself
    // can block indefinitely. Dump committed trace slots before terminating.
    std::mutex watchdogMutex;
    std::condition_variable watchdogCv;
    bool finished = false;
    std::thread watchdog([&] {
        std::unique_lock<std::mutex> lock(watchdogMutex);
        if (!watchdogCv.wait_for(lock, std::chrono::seconds(12), [&]{return finished;})) {
            burst::emit("watchdog", nullptr);
            burst::dump(trace);
            std::cerr << "watchdog: blocked submission/completion; trace saved\n";
            std::_Exit(124);
        }
    });
    rogue::Logging::setLevel(rogue::Logging::Critical);
    auto stack = std::make_shared<burst::Stack>(burst::envUnsigned("BURST_SEGMENT", 1400),
                                              burst::envUnsigned("BURST_RSSI_WINDOW", 32),
                                              std::stoul(argv[9]), transport);
    auto client = stack->client;
    auto server = stack->server;
    auto srp = stack->srp;
    auto out = stack->out;
    auto in = stack->in;
    auto master = rim::Master::create();
    auto hub = rim::Hub::create(0, 0, 0);
    hub->setSlave(srp);
    master->setSlave(split ? std::static_pointer_cast<rim::Slave>(hub) : std::static_pointer_cast<rim::Slave>(srp));
    master->setTimeout(3000000);
    server->start(); client->start();
    auto deadline = burst::now()+5000000000ULL;
    while (!(client->getOpen() && server->getOpen()) && burst::now() < deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    bool ok = stack->open();
    // Initialize distinct pages before timing. Every response is checked.
    std::vector<std::vector<uint8_t>> data(count, std::vector<uint8_t>(size));
    for (unsigned i = 0; ok && i < count; ++i) {
        for (unsigned j = 0; j < size; ++j) data[i][j] = (i*17+j*7)&255;
        auto id = master->reqTransaction(static_cast<uint64_t>(i)*4096, size, data[i].data(), rim::Write);
        master->waitTransaction(id);
        ok = master->getError().empty();
        std::fill(data[i].begin(), data[i].end(), 0);
    }
    burst::emit("measure_begin", nullptr, window, size, count);
    burst::armed = true;
    auto start = burst::now();
    unsigned completed = 0;
    if (split) {
        // Full-sized adjacent SRP children share one parent mutex via Hub.
        // This diagnostic is separate from the independent-request sweep.
        std::vector<uint8_t> block(static_cast<uint64_t>(count)*4096);
        auto id = master->reqTransaction(0, block.size(), block.data(), rim::Read);
        master->waitTransaction(id);
        ok = ok && master->getError().empty();
        for (unsigned i = 0; ok && i < count; ++i)
            for (unsigned j = 0; j < size; ++j)
                if (block[i*4096+j] != uint8_t((i*17+j*7)&255)) ok = false;
        if (ok) completed = count;
    } else {
        // Fixed bursts: issue up to WINDOW then wait; WINDOW=1 is sequential.
        for (unsigned base = 0; ok && base < count; base+=window) {
            std::vector<uint32_t> ids(std::min(count-base, window));
            auto end = std::min(count, base+window);
            auto submit = [&](unsigned worker) {
                for (unsigned i = base+worker; i < end; i+=workers)
                    ids[i-base] = master->reqTransaction(static_cast<uint64_t>(i)*4096, size, data[i].data(), rim::Read);
            };
            if (workers == 1) {
                submit(0);
            } else {
                std::vector<std::thread> producers;
                for (unsigned worker = 0; worker < workers; ++worker) producers.emplace_back(submit, worker);
                for (auto& producer : producers) producer.join();
            }
            for (unsigned i = base; i < end; ++i) {
                master->waitTransaction(ids[i-base]);
                if (!master->getError().empty()) ok = false;
                for (unsigned j = 0; j < size; ++j)
                    if (data[i][j] != uint8_t((i*17+j*7)&255)) ok = false;
                if (ok) ++completed;
            }
        }
    }
    auto elapsed = burst::now()-start;
    burst::emit("measure_end", nullptr, completed, ok, elapsed);
    std::cout << "{\"ok\":" << (ok ? "true" : "false") << ",\"completed\":" << completed
              << ",\"elapsed_ms\":" << elapsed/1e6 << ",\"retransmits\":"
              << client->getRetranCount()+server->getRetranCount() << ",\"resets\":"
              << client->getDownCount()+server->getDownCount() << ",\"events\":" << burst::next.load()
              << ",\"trace_overflow\":" << (burst::next.load() > burst::capacity ? "true" : "false") << "}\n";
    burst::armed = false;
    client->stop(); server->stop(); out->stop(); in->stop();
    burst::dump(trace);
    { std::lock_guard<std::mutex> lock(watchdogMutex); finished = true; }
    watchdogCv.notify_one(); watchdog.join();
    // Old revisions contain ownership cycles and have no uniform stop API.
    // Each case is process-isolated; avoid relying on historical destructors.
    std::cout.flush(); std::_Exit(ok ? 0 : 1);
}
