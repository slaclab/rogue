# DETECTED — Stream Subsystem Partial

**Phase:** 01 / Plan 01
**Scope:** src/rogue/interfaces/stream/, include/rogue/interfaces/stream/,
src/rogue/interfaces/ (top-level ZMQ), include/rogue/interfaces/ (top-level ZMQ)
**Branch:** hunt-for-red-october
**Generated:** 2026-04-23

## Files Reviewed

src/rogue/interfaces/stream/Buffer.cpp
src/rogue/interfaces/stream/Fifo.cpp
src/rogue/interfaces/stream/Filter.cpp
src/rogue/interfaces/stream/Frame.cpp
src/rogue/interfaces/stream/FrameIterator.cpp
src/rogue/interfaces/stream/FrameLock.cpp
src/rogue/interfaces/stream/Master.cpp
src/rogue/interfaces/stream/module.cpp
src/rogue/interfaces/stream/Pool.cpp
src/rogue/interfaces/stream/RateDrop.cpp
src/rogue/interfaces/stream/Slave.cpp
src/rogue/interfaces/stream/TcpClient.cpp
src/rogue/interfaces/stream/TcpCore.cpp
src/rogue/interfaces/stream/TcpServer.cpp
include/rogue/interfaces/stream/Buffer.h
include/rogue/interfaces/stream/Fifo.h
include/rogue/interfaces/stream/Filter.h
include/rogue/interfaces/stream/FrameAccessor.h
include/rogue/interfaces/stream/Frame.h
include/rogue/interfaces/stream/FrameIterator.h
include/rogue/interfaces/stream/FrameLock.h
include/rogue/interfaces/stream/Master.h
include/rogue/interfaces/stream/module.h
include/rogue/interfaces/stream/Pool.h
include/rogue/interfaces/stream/RateDrop.h
include/rogue/interfaces/stream/Slave.h
include/rogue/interfaces/stream/TcpClient.h
include/rogue/interfaces/stream/TcpCore.h
include/rogue/interfaces/stream/TcpServer.h
src/rogue/interfaces/ZmqClient.cpp
src/rogue/interfaces/ZmqServer.cpp
src/rogue/interfaces/module.cpp
include/rogue/interfaces/ZmqClient.h
include/rogue/interfaces/ZmqServer.h
include/rogue/interfaces/module.h

## Findings

| ID | File | Lines | Class | Severity | Description | Status | Repro Hypothesis | Reference |
|---|---|---|---|---|---|---|---|---|
| STREAM-001 | include/rogue/interfaces/stream/Fifo.h | 46 | threading | high | dropFrameCnt_ and threadEn_ were non-atomic fields read from runThread while written from acceptFrame/destructor without synchronization | fixed-in-b1a669c96 | TSan race under N×parallel Fifo push vs runThread read | CONCERNS.md §Thread-Safety-Concerns / Fifo Non-Atomic Flags |
| STREAM-002 | src/rogue/interfaces/stream/FrameLock.cpp | 65-77 | threading | low | FrameLock::lock() and unlock() use raw frame_->lock_.lock()/unlock() calls without RAII; exception between unlock at line 76 and locked_=false on line 77 is not possible in practice but pattern is fragile | detected | Exception path in future Python callback calling lock()/unlock() could wedge frame lock | CONCERNS.md §Test-Coverage-Gaps / FrameLock Manual Unlock Path |
| STREAM-003 | include/rogue/interfaces/stream/TcpCore.h | 76 | threading | high | threadEn_ is plain bool read in runThread() worker and written in stop() from a different thread without atomic or memory-order guarantee | detected | TSan race between TcpCore::stop() and TcpCore::runThread() on threadEn_ under normal connect/disconnect cycle | |
| STREAM-004 | include/rogue/interfaces/ZmqClient.h | 70-71 | threading | high | threadEn_ and running_ are plain bool fields written in stop() and constructor from caller thread while runThread() reads threadEn_ in a tight loop without atomic or fence | detected | TSan race between ZmqClient::stop() and ZmqClient::runThread() on threadEn_; stop() may also race with constructor on running_ if shared before thread starts | |
| STREAM-005 | include/rogue/interfaces/ZmqServer.h | 63 | threading | high | threadEn_ is plain bool written in stop() from caller thread and read in runThread()/strThread() workers without atomic or fence | detected | TSan race between ZmqServer::stop() and the two worker threads on threadEn_ | |
| STREAM-006 | src/rogue/interfaces/stream/Slave.cpp | 82-83 | threading | medium | frameCount_ and frameBytes_ are plain uint64_t incremented in acceptFrame() which can be called concurrently from multiple Masters without a lock protecting the counters | detected | TSan race when two Masters send frames to same Slave concurrently; narrow window but reachable in normal multi-master configurations | |
| STREAM-007 | src/rogue/interfaces/stream/Pool.cpp | 59-65 | threading | medium | getAllocBytes() and getAllocCount() read allocBytes_ and allocCount_ without holding mtx_; writes to these fields happen under mtx_ in allocBuffer()/retBuffer()/createBuffer()/decCounter(), so reads from Python via PyRogue poll threads race with buffer alloc/return | detected | TSan race between polling thread calling getAllocBytes() and DMA/stream worker calling retBuffer() | |
| STREAM-008 | src/rogue/interfaces/stream/RateDrop.cpp | 85-98 | threading | medium | dropCount_, nextPeriod_, and timePeriod_ are plain non-atomic members read and written in acceptFrame() without a lock; if two Masters feed the same RateDrop concurrently both threads can race on dropCount_ increment and nextPeriod_ update | detected | TSan race when two Slave callers of acceptFrame() run concurrently on a shared RateDrop instance | |
| STREAM-009 | src/rogue/interfaces/stream/Slave.cpp | 110-123 | threading | low | SlaveWrap::acceptFrame() acquires ScopedGil then calls this->get_override() — the ScopedGil is correctly used here since SlaveWrap::acceptFrame() is invoked from C++ worker threads that do not hold the GIL; usage is correct but ambiguous: the call site where Slave::acceptFrame() is invoked from a C++ thread (e.g. Fifo::runThread) confirms wrong-direction concern is absent | detected | GIL-origin audit shows ScopedGil acquisition is correct for C++ worker → Python callback path | |
| STREAM-010 | src/rogue/interfaces/ZmqClient.cpp | 354-366 | threading | low | ZmqClient::runThread() acquires ScopedGil inside the C++ std::thread worker to call doUpdate(); this is correct (worker does not hold GIL, ScopedGil acquires it), but the pattern is flagged as ambiguous per failure-mode 2: GilRelease/ScopedGil inside cpp-worker — thread origin is a C++ std::thread | detected | GIL-origin audit: ScopedGil in std::thread worker is correct direction; cross-reference GIL plan 06 for completeness | |
| STREAM-011 | src/rogue/interfaces/ZmqServer.cpp | 293-316 | threading | low | ZmqServer::runThread() acquires ScopedGil inside the C++ std::thread worker to dispatch doRequest(); same correct-direction pattern as STREAM-010 but flagged for GIL plan 06 completeness audit | detected | GIL-origin audit: ScopedGil in std::thread worker is correct direction; cross-reference GIL plan 06 | |
| STREAM-012 | src/rogue/interfaces/ZmqServer.cpp | 263-272 | threading | low | ZmqServerWrap::doString() acquires ScopedGil inside strThread() which is a std::thread worker; correct-direction usage (worker does not hold GIL) but flagged for GIL plan 06 completeness audit | detected | GIL-origin audit: ScopedGil in std::thread worker is correct direction; cross-reference GIL plan 06 | |
| STREAM-013 | src/rogue/interfaces/stream/TcpCore.cpp | 175-222 | threading | medium | TcpCore::acceptFrame() holds both frame lock and bridgeMtx_ simultaneously (lock ordering: frame lock first, then bridgeMtx_); runThread() holds only bridgeMtx_ implicitly via reqLocalFrame; if another path acquires bridgeMtx_ before frame lock the lock ordering is reversed, creating a potential deadlock | detected | Deadlock if concurrent acceptFrame() and a future code path acquires bridgeMtx_ before calling frame->lock() | |
| STREAM-014 | src/rogue/interfaces/stream/FrameIterator.cpp | 83-88 | memory | low | decrement() sets framePos_ to frameSize_ (sentinel end-of-frame) when decrement goes below zero, mirroring increment(); this makes past-beginning equal to end, which is counter-intuitive and could cause silent data access past buffer start if caller does not check for this | detected | Unit test: decrement an iterator below begin() and verify data_ is NULL | |

## Notes

- Severity calibration per D-07 rubric; consolidation plan normalizes outliers.
- STREAM-001: mandatory hotspot row per ROADMAP SC-1; Status fixed-in-b1a669c96 per CONCERNS.md.
- STREAM-002: FrameLock manual unlock fragility at lines 65-77 as required hotspot. The RAII destructor at line 61 does correctly release the lock, so the destructor path is safe. The risk is limited to exceptions inside the lock()/unlock() C++ API if callers misuse them directly. Severity low per D-07 rubric (no evidence fires in normal use).
- No findings for src/rogue/interfaces/stream/Filter.cpp: simple channel/error filter with no shared state — filter fields (dropErrors_, channel_) are set only in constructor and read-only thereafter; no threading issue.
- No findings for src/rogue/interfaces/stream/Buffer.cpp: frame_.lock() calls at lines 101-252 are weak_ptr::lock() (not mutex lock); the pattern with null-check is correct (tmpPtr null check present on every call).
- No findings for src/rogue/interfaces/stream/FrameIterator.cpp: iterator state is per-instance with no shared mutable state across threads; STREAM-014 logs a semantic edge case only.
- No findings for src/rogue/interfaces/stream/Master.cpp: slaveMtx_ guards slaves_ via lock_guard on all accesses; no raw lock/unlock.
- No findings for src/rogue/interfaces/stream/Frame.cpp: lock_ mutex is accessed only via FrameLock RAII wrapper; metadata fields (flags_, error_, chan_) are not individually guarded but are accessed only while frame lock is held per API contract.
- No findings for include/rogue/interfaces/stream/FrameAccessor.h: header-only template, constructs with bounds check, no threading surface.
- No findings for src/rogue/interfaces/stream/TcpClient.cpp, src/rogue/interfaces/stream/TcpServer.cpp: thin wrappers delegating to TcpCore; no independent state.
- No findings for src/rogue/interfaces/stream/module.cpp, src/rogue/interfaces/module.cpp, include/rogue/interfaces/stream/module.h, include/rogue/interfaces/module.h: module registration stubs with no runtime state.
- No findings for include/rogue/interfaces/stream/TcpClient.h, include/rogue/interfaces/stream/TcpServer.h: declaration-only wrappers.
- STREAM-009, STREAM-010, STREAM-011, STREAM-012: GilRelease/ScopedGil sites in C++ worker threads are correct-direction (workers re-acquire GIL to call Python); flagged for GIL plan 06 completeness cross-reference, not as bugs. Severity low.
- rogueStreamTap macro (CONCERNS.md §Tech-Debt): grep confirms no usage in stream subsystem files reviewed here; the macro definition is in include/rogue/Helpers.h (out of this partition's scope), and usage sites are not in stream/ or ZMQ top-level files.
