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
#ifndef SRP_RSSI_TRACE_H
#define SRP_RSSI_TRACE_H
#include <atomic>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <cstdlib>
#include <functional>
#include <sstream>
#include <thread>
#include <string>

namespace burst {
struct Event {
    std::atomic<bool> ready{false};
    uint64_t ns, thread, object, a, b, c;
    const char* name;
};
constexpr size_t capacity = 2000000;
extern Event events[capacity];
extern std::atomic<size_t> next;
extern std::atomic<bool> enabled;
extern std::atomic<bool> armed;
extern const void* appTarget;
extern const void* srpTarget;
extern const void* txTarget;
extern std::string mode;
extern bool constructingPeer;
inline unsigned envUnsigned(const char* name, unsigned fallback) {
    const char* value = std::getenv(name);
    return value ? std::stoul(value) : fallback;
}
extern unsigned delayMs;
extern unsigned stallAfter;
extern std::atomic<unsigned> stallHits;
inline uint64_t now() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
inline void emit(const char* name, const void* object, uint64_t a = 0, uint64_t b = 0, uint64_t c = 0) {
    if (!enabled.load(std::memory_order_relaxed)) return;
    auto i = next.fetch_add(1, std::memory_order_relaxed);
    if (i >= capacity) return;
    auto& e = events[i];
    e.ns = now();
    e.thread = std::hash<std::thread::id>{}(std::this_thread::get_id());
    e.object = reinterpret_cast<uintptr_t>(object);
    e.name = name; e.a = a; e.b = b; e.c = c;
    e.ready.store(true, std::memory_order_release);
}
struct Scope {
    const char* name;
    const void* object;
    uint64_t start;
    Scope(const char* n, const void* o) : name(n), object(o), start(now()) { emit(n, o, 0); }
    ~Scope() { emit(name, object, 1, now()-start); }
};
inline void stall(const char* site, const void* object) {
    if (mode != site || !armed.load()) return;
    if ((mode == "app" && object != appTarget) ||
        ((mode == "srp" || mode == "submit") && object != srpTarget) ||
        (mode == "tx" && object != txTarget)) return;
    if (stallHits.fetch_add(1) + 1 != stallAfter) return;
    if (!armed.exchange(false)) return;
    emit("stall_begin", object, delayMs);
    std::this_thread::sleep_for(std::chrono::milliseconds(delayMs));
    emit("stall_end", object);
}
inline void dump(const std::string& path) {
    std::ofstream f(path);
    f << "ns,thread,event,object,a,b,c\n";
    const auto n = next.load();
    for (size_t i = 0; i < n && i < capacity; ++i) {
        auto& e = events[i];
        if (e.ready.load(std::memory_order_acquire))
            f << e.ns << ',' << e.thread << ',' << e.name << ',' << e.object << ','
              << e.a << ',' << e.b << ',' << e.c << '\n';
    }
}
}  // namespace burst
#endif
