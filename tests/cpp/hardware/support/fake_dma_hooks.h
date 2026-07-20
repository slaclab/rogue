/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * Shared C++ accessors for the fake_dma_preload LD_PRELOAD test shim.
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
#ifndef ROGUE_TEST_CPP_HARDWARE_SUPPORT_FAKE_DMA_HOOKS_H
#define ROGUE_TEST_CPP_HARDWARE_SUPPORT_FAKE_DMA_HOOKS_H

#include <dlfcn.h>
#include <stdint.h>

#include <stdexcept>

namespace rogue_test {

class FakeDma {
  public:
    using PathFn        = const char* (*)();
    using ResetFn       = void (*)();
    using BlockNextFn   = void (*)();
    using WaitBlockedFn = int (*)(uint32_t);
    using ReleaseFn     = void (*)();
    using CountFn       = int (*)();

    FakeDma() {
        path_            = load<PathFn>("fakedma_path");
        reset_           = load<ResetFn>("fakedma_reset");
        blockNext_       = load<BlockNextFn>("fakedma_block_next_ret_index");
        waitBlocked_     = load<WaitBlockedFn>("fakedma_wait_blocked");
        release_         = load<ReleaseFn>("fakedma_release_blocked");
        mappedCount_     = load<CountFn>("fakedma_mapped_count");
        fdCount_         = load<CountFn>("fakedma_fd_count");
        regionCount_     = load<CountFn>("fakedma_region_count");
        activeCalls_     = load<CountFn>("fakedma_active_call_count");
        overflowCount_   = load<CountFn>("fakedma_tracking_overflow_count");
        isClean_         = load<CountFn>("fakedma_is_clean");
        retIndexCount_     = load<CountFn>("fakedma_ret_index_count");
        closeDuringCall_   = load<CountFn>("fakedma_close_during_driver_call");
    }

    const char* path() const { return path_(); }
    void reset() const { reset_(); }
    void blockNextRetIndex() const { blockNext_(); }
    bool waitBlocked(uint32_t timeoutMs) const { return waitBlocked_(timeoutMs) != 0; }
    void releaseBlocked() const { release_(); }
    int mappedCount() const { return mappedCount_(); }
    int fdCount() const { return fdCount_(); }
    int regionCount() const { return regionCount_(); }
    int activeCallCount() const { return activeCalls_(); }
    int overflowCount() const { return overflowCount_(); }
    bool isClean() const { return isClean_() != 0; }
    int retIndexCount() const { return retIndexCount_(); }
    bool closeDuringDriverCall() const { return closeDuringCall_() != 0; }

  private:
    template <typename Func>
    Func load(const char* name) {
        dlerror();
        void* sym = dlsym(RTLD_DEFAULT, name);
        if (sym == nullptr) {
            const char* err = dlerror();
            throw std::runtime_error(err != nullptr ? err : name);
        }
        return reinterpret_cast<Func>(sym);
    }

    PathFn path_;
    ResetFn reset_;
    BlockNextFn blockNext_;
    WaitBlockedFn waitBlocked_;
    ReleaseFn release_;
    CountFn mappedCount_;
    CountFn fdCount_;
    CountFn regionCount_;
    CountFn activeCalls_;
    CountFn overflowCount_;
    CountFn isClean_;
    CountFn retIndexCount_;
    CountFn closeDuringCall_;
};

inline FakeDma& fakeDma() {
    static FakeDma fake;
    return fake;
}

}  // namespace rogue_test

#endif
