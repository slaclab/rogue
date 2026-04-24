# Hardware + Core + Utilities + interfaces/api/ — Raw Findings (Partial)

**Subsystem:** hw-core
**ID Prefix:** HW-CORE-###
**Reviewed:** 2026-04-23 on branch `hunt-for-red-october` (HEAD 1a04b1e1f)
**Consolidation target:** `.planning/audit/DETECTED.md` via plan 01-07

---

## Files Reviewed

### Core top-level (src/rogue/)
- `src/rogue/module.cpp`
- `src/rogue/GeneralError.cpp`
- `src/rogue/GilRelease.cpp`
- `src/rogue/Logging.cpp`
- `src/rogue/ScopedGil.cpp`
- `src/rogue/Version.cpp`

### Core top-level headers (include/rogue/)
- `include/rogue/Directives.h`
- `include/rogue/EnableSharedFromThis.h`
- `include/rogue/GeneralError.h`
- `include/rogue/GilRelease.h`
- `include/rogue/Helpers.h`
- `include/rogue/Logging.h`
- `include/rogue/module.h`
- `include/rogue/numpy.h`
- `include/rogue/Queue.h`
- `include/rogue/ScopedGil.h`
- `include/rogue/Version.h`

### Hardware (src/rogue/hardware/)
- `src/rogue/hardware/MemMap.cpp`
- `src/rogue/hardware/module.cpp`
- `src/rogue/hardware/axi/AxiMemMap.cpp`
- `src/rogue/hardware/axi/AxiStreamDma.cpp`
- `src/rogue/hardware/axi/module.cpp`

### Hardware headers (include/rogue/hardware/)
- `include/rogue/hardware/MemMap.h`
- `include/rogue/hardware/module.h`
- `include/rogue/hardware/axi/AxiMemMap.h`
- `include/rogue/hardware/axi/AxiStreamDma.h`
- `include/rogue/hardware/axi/module.h`
- `include/rogue/hardware/drivers/AxisDriver.h`
- `include/rogue/hardware/drivers/DmaDriver.h`

### interfaces/api/ — Board Support Package facade (D-12 coverage)
- `src/rogue/interfaces/api/Bsp.cpp`
- `include/rogue/interfaces/api/Bsp.h`

### Utilities (src/rogue/utilities/)
- `src/rogue/utilities/module.cpp`
- `src/rogue/utilities/Prbs.cpp`
- `src/rogue/utilities/StreamUnZip.cpp`
- `src/rogue/utilities/StreamZip.cpp`
- `src/rogue/utilities/fileio/module.cpp`
- `src/rogue/utilities/fileio/StreamReader.cpp`
- `src/rogue/utilities/fileio/StreamWriter.cpp`
- `src/rogue/utilities/fileio/StreamWriterChannel.cpp`

### Utilities headers (include/rogue/utilities/)
- `include/rogue/utilities/module.h`
- `include/rogue/utilities/Prbs.h`
- `include/rogue/utilities/StreamUnZip.h`
- `include/rogue/utilities/StreamZip.h`
- `include/rogue/utilities/fileio/module.h`
- `include/rogue/utilities/fileio/StreamReader.h`
- `include/rogue/utilities/fileio/StreamWriter.h`
- `include/rogue/utilities/fileio/StreamWriterChannel.h`

---

## Findings Table

| ID | File | Lines | Class | Severity | Description | Status | Repro Hypothesis | Reference |
|----|------|-------|-------|----------|-------------|--------|-----------------|-----------|
| HW-CORE-001 | src/rogue/Logging.cpp | 109-112 | threading | high | `levelMtx_.lock()` called in `Logging::Logging` ctor at line 109; `warning()` at line 114 is called *after* `levelMtx_.unlock()` at line 112, but an exception thrown by any code between lock and unlock (e.g., in `updateLevelLocked` or `loggers_.push_back`) would exit without releasing `levelMtx_`, permanently wedging any subsequent logger creation or `setLevel`/`setFilter` call. | detected | Throw `std::bad_alloc` from `loggers_.push_back` with address-space pressure before `levelMtx_.unlock()`; subsequent `Logging::create` call will deadlock. | CONCERNS.md §Known-Bugs §Logging-Mutex-Manual-Lock-Unlock |
| HW-CORE-002 | src/rogue/Logging.cpp | 120-127, 146-149, 155-163, 167-176, 181-183, 188-190 | threading | high | Six additional raw `levelMtx_.lock()` / `levelMtx_.unlock()` pairs in `~Logging`, `setLevel`, `setFilter`, `setForwardPython`, `forwardPython`, `setEmitStdout`, and `emitStdout`; none are exception-safe. Although the current bodies contain no direct throws, future edits to these functions face the same invariant violation risk, and a thrown exception in `new rogue::LogFilter(...)` inside `setFilter` (line 157) would leak the lock. The heap allocation (`new`) inside the locked region (line 157, `setFilter`) is the most concrete danger today. | detected | Inject allocation failure via `LD_PRELOAD` or sanitizer fault-injection while calling `Logging::setFilter` under thread contention; deadlock on next `setLevel`. | CONCERNS.md §Known-Bugs §Logging-Mutex-Manual-Lock-Unlock |
| HW-CORE-003 | include/rogue/Queue.h | 47, 99, 150 | threading | medium | `Queue::busy_` was a non-atomic `bool` read lock-free from `busy()` while being updated under `mtx_` lock in `push()` and `pop()`; this is a data race. Converted to `std::atomic<bool>` in commit `b1a669c96`; the lock-free read pattern is now safe but the comment in the original code was absent, making future refactors risky. | fixed-in-b1a669c96 | TSan race under parallel `push`/`pop` + `busy()` calls; no longer triggerable post-fix. | CONCERNS.md §Thread-Safety-Concerns §Queue-Busy-Flag-Non-Atomic |
| HW-CORE-004 | include/rogue/Helpers.h | 25-27 | logic | low | `rogueStreamTap` macro is marked DEPRECATED in the comment but remains present; it is a byte-for-byte alias of `rogueStreamConnect`, so it will silently do the right thing but blocks removal of the old API name and may confuse new developers about stream-tap semantics. | detected | No runtime failure expected; audit finding for code-cleanliness and documentation correctness. | CONCERNS.md §Tech-Debt §Deprecated-Stream-Tap-Macro |
| HW-CORE-005 | src/rogue/GilRelease.cpp | 41-45, 48-54 | threading | low | `GilRelease::acquire()` calls `PyEval_RestoreThread(state_)` unconditionally when `state_ != NULL`; if the caller has already re-acquired the GIL externally (e.g., via `ScopedGil` in a nested scope) and then calls `acquire()` explicitly, the internal `state_` pointer will be stale but re-used, resulting in undefined behavior on CPython's thread-state stack. The API allows both explicit `acquire()`/`release()` and automatic RAII use, but there is no assertion protecting against nested or double-acquire. `release()` is safe (it checks `PyGILState_Check()`), but `acquire()` does not verify the thread state is still the one previously saved. | detected | Construct two nested `GilRelease` scopes, call inner `.acquire()` manually, then allow outer dtor to re-acquire; this double-restores on CPython <= 3.12 and may crash. | — |
| HW-CORE-006 | src/rogue/hardware/axi/AxiStreamDma.cpp | 45 | threading | medium | `rha::AxiStreamDma::sharedBuffers_` is a static `std::map` modified by `openShared`, `closeShared`, and `zeroCopyDisable` without any lock; if two `AxiStreamDma` objects are constructed concurrently for different paths, both will call `openShared` simultaneously, racing on `sharedBuffers_.find` and `sharedBuffers_.insert`. | detected | Construct two `AxiStreamDma` instances with different device paths from two Python threads simultaneously; TSan should flag the unsynchronized map operations. | — |
| HW-CORE-007 | src/rogue/hardware/axi/AxiStreamDma.cpp | 192-215 | memory | medium | `AxiStreamDma` constructor opens the shared buffer structure (`openShared`) and the non-shared file descriptor; if `dmaSetMaskBytes` (line 208) fails, `closeShared(desc_)` and `::close(fd_)` are called and an exception is thrown. However, if the failure occurs at `::open(path, O_RDWR)` (line 192) and `openShared` succeeded but the exception path at line 195 calls `closeShared(desc_)` before `fd_` is assigned, `fd_` is never set to `-1` in `stop()` guard — `stop()` checks `threadEn_` only, so a partially-constructed object whose thread was never started would call `closeShared` without ever setting `threadEn_`, making `stop()` a no-op while `desc_` ownership is ambiguous. | detected | Inject `open` failure via `LD_PRELOAD`; check that the shared descriptor reference count is correctly decremented and no double-close of `fd_` occurs. | — |
| HW-CORE-008 | src/rogue/hardware/axi/AxiStreamDma.cpp | 502 | threading | low | In `AxiStreamDma::runThread`, the loop condition `while (threadEn_)` reads `threadEn_` (a plain `bool` class member) from a `std::thread` worker without an atomic load or memory fence; `stop()` sets `threadEn_ = false` from the calling thread. The C++11 memory model requires `std::atomic` or a synchronization event for a write in one thread to be visible in another. On x86 this is benign due to coherent cache but is technically undefined behavior (data race on a non-atomic `bool`). | detected | TSan will flag this as a data race when `stop()` and `runThread()` execute concurrently on any relaxed-memory-order platform. | — |
| HW-CORE-009 | src/rogue/hardware/axi/AxiStreamDma.cpp | 184 | threading | low | `rogue::GilRelease noGil` is used in the `AxiStreamDma` constructor (line 184), which is called from the Python-originated `__init__` (via Boost.Python); this is the correct direction for a blocking `openShared`/`open` call. No bug here. Cross-ref plan 06 (GilRelease call-site audit) for completeness. | detected | n/a — correct usage; logged for GIL completeness audit. | CONCERNS.md §Thread-Safety-Concerns §GIL-Release-Pattern |
| HW-CORE-010 | src/rogue/hardware/MemMap.cpp | 63-65 | memory | medium | In `MemMap::MemMap`, if `mmap` fails (returns `MAP_FAILED`), a `GeneralError` exception is thrown but `fd_` (already opened at line 59) is not closed before the throw; the file descriptor leaks on the exception path. | detected | Inject `mmap` failure via `ulimit -v` or a mock; check that no fd leak occurs when the constructor throws. | — |
| HW-CORE-011 | src/rogue/hardware/axi/AxiMemMap.cpp | 63-69 | memory | medium | In `AxiMemMap::AxiMemMap`, the version check at line 63 throws `GeneralError` without closing `fd_` (opened at line 57); the file descriptor leaks on the exception path. The subsequent version check at line 73 does call `::close(fd_)` before throwing, so that path is correct, but the first `dmaGetApiVersion` check at line 63 does not. | detected | Open device with an old driver API; verify no fd leak when the first version check fails. | — |
| HW-CORE-012 | src/rogue/utilities/Prbs.cpp | 244-246 | threading | high | `Prbs::setRxEnable` calls `pMtx_.lock()` / `pMtx_.unlock()` directly (raw lock/unlock) rather than using `std::lock_guard`; any exception between the lock and unlock calls would leak the mutex. No current exception source exists inside this specific two-line critical section, but the pattern is an immediate `threading` bug per convention (same class as `Logging.cpp`). | detected | No immediate throw path; future edits that add validation inside the critical section would silently create a deadlock. — Severity: high because raw lock/unlock is a rule violation that could deadlock entire Prbs. | — |
| HW-CORE-013 | src/rogue/utilities/Prbs.cpp | 321-330 | threading | high | `Prbs::resetCount` calls `pMtx_.lock()` / `pMtx_.unlock()` directly without RAII; the comment in the source ("Counters should really be locked!") was present before the locking was added and remains, indicating this was known to be unsafe. Same raw-lock pattern as HW-CORE-012. | detected | No current throw path inside the critical section; risk is from future edits or `std::bad_alloc` from counter write on overloaded allocator (extremely unlikely). Same deadlock blast-radius as HW-CORE-012. | — |
| HW-CORE-014 | src/rogue/utilities/Prbs.cpp | 202-205 | threading | medium | `Prbs::runThread` reads `threadEn_` (a plain non-atomic `bool` declared in the class) and `txSize_` without holding `pMtx_`; `disable()` sets `threadEn_ = false` from the calling thread while `runThread` reads it concurrently. On relaxed-memory-order architectures this is a data race. `txSize_` is similarly read in the loop body without a lock while `enable()` sets it before spawning the thread (which is safe), but `genFrame` reads `txSize_` inside `pMtx_` lock, so the runThread read is inconsistent. | detected | TSan will flag `threadEn_` and `txSize_` reads in `runThread` as races with `disable()` and `enable()`. | — |
| HW-CORE-015 | src/rogue/interfaces/api/Bsp.cpp | 55 | logic | medium | `Bsp::Bsp(modName, rootClass)` waits for the Python root to become running with `while (bp::extract<bool>(this->_obj.attr("running")) == false) usleep(10)` without any timeout; if the root fails to start or throws an exception that leaves `running` permanently false, this constructor loops forever with no escape. | detected | Construct `Bsp` from a `rootClass` that never sets `running=True`; the caller blocks forever. Stress: raise an exception in the root's `start()` method. | — |
| HW-CORE-016 | src/rogue/interfaces/api/Bsp.cpp | 40-44, 46-56 | threading | medium | All `Bsp` methods (`getAttribute`, `operator[]`, `getNode`, `operator()`, `set`, `setWrite`, `get`, `readGet`) call into Boost.Python on `this->_obj` without holding the GIL explicitly; these methods are expected to be called from C++ contexts that may not hold the GIL. Without `ScopedGil`, any C++-originated call to these methods races with CPython's GC and reference-counting machinery. | detected | Call `Bsp::getAttribute` from a plain `std::thread` while the Python GIL is not held; TSan or CPython debug build will flag refcount corruption. | — |
| HW-CORE-017 | src/rogue/utilities/StreamUnZip.cpp | 98-101 | memory | medium | In `StreamUnZip::acceptFrame`, when `strm.avail_in == 0`, the code unconditionally advances `rBuff` and dereferences it (`strm.next_in = reinterpret_cast<char*>((*rBuff)->begin())`); if all input buffers have been consumed and `avail_in` hits zero *without* the decompressor having signaled `BZ_STREAM_END`, the iterator advances past `endBuffer()` and is dereferenced out of bounds. This is a latent UAF/OOB if BZip2 produces more output than the input being consumed (which is impossible by design but the code provides no bounds assertion). | detected | Feed a corrupt or prematurely-truncated bzip2 stream; if `BZ2_bzDecompress` returns `BZ_OK` with `avail_in==0` and `avail_out>0`, the iterator overflow will occur. | — |
| HW-CORE-018 | src/rogue/utilities/fileio/StreamReader.cpp | 180-231 | threading | medium | `StreamReader::runThread` accesses `fd_` (read at line 180, written in `intClose` via line 144) without holding `mtx_`; `close()` acquires `mtx_` and calls `intClose()`, which sets `threadEn_ = false` and joins the thread — but the data race on `fd_` between the thread loop and any concurrent `close()` call that sets `fd_ = -1` (line 144 in `intClose`) while `runThread` reads `fd_` is a TSan-flagged race. | detected | Call `close()` from the main thread while `runThread` is active reading the file; TSan should flag the unsynchronized `fd_` access. | — |
| HW-CORE-019 | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 87-88 | threading | low | `StreamWriterChannel::frameCount_` is incremented (line 87) while holding `mtx_` lock (line 86) inside `acceptFrame`, and also read/written in `getFrameCount()` (line 91, no lock) and `setFrameCount()` (line 96, takes lock). `getFrameCount()` reads `frameCount_` without any lock, which is a data race with concurrent `acceptFrame` calls; the `uint32_t` read is likely atomic on x86 but is formally undefined behavior per the C++11 memory model. | detected | Concurrent `acceptFrame` + `getFrameCount` calls; TSan will flag the unlocked read in `getFrameCount`. | — |
| HW-CORE-020 | include/rogue/hardware/drivers/DmaDriver.h | 399-423 | logic | low | `dmaReadBulkIndex` uses a C99 variable-length array `struct DmaReadData r[count]` (line 407); VLAs are not part of the C++11/14/17 standard (they are a GCC extension). If `count` is 0 or very large, this produces either a zero-length VLA (UB in C++) or a stack overflow. The caller (`AxiStreamDma::runThread`) passes `RxBufferCount` which is a compile-time constant, so in practice the size is fixed, but the API signature does not enforce this and a future caller supplying a dynamic count could trigger stack overflow or a C++-dialect portability issue. | detected | Call `dmaReadBulkIndex` with `count=0` or `count > stack_frame_size / sizeof(DmaReadData)`. | — |

---

## Notes

- **HW-CORE-009** is a correct GIL usage; logged for completeness for plan 06 (GilRelease call-site audit).
- **HW-CORE-005** (GilRelease double-acquire): the `release()` half is safe because it checks `PyGILState_Check()`; only the `acquire()` direction is risky for nested use.
- **HW-CORE-006** (sharedBuffers_ data race): in practice all hardware paths are opened during PyRogue root startup while the GIL is held and before worker threads start, reducing real-world exposure, but the lack of synchronization is formally a data race.
- **HW-CORE-016** (Bsp GIL missing): the typical calling pattern from Python always holds the GIL, so this is low real-world risk; it becomes high risk if a future C++ caller uses `Bsp` from a worker thread, which the API explicitly supports via the `create(modName, rootClass)` factory that calls `Py_Initialize()`.
- `src/rogue/module.cpp`, `src/rogue/hardware/module.cpp`, `src/rogue/hardware/axi/module.cpp`, and all `utilities/*/module.cpp` were reviewed; they contain only Boost.Python `setup_python()` registration calls — no threading, memory, or logic bugs found.
- `include/rogue/Directives.h`, `include/rogue/numpy.h`, `include/rogue/module.h` — reviewed; build configuration and thin wrappers only; no findings.
- `include/rogue/GeneralError.h`, `include/rogue/Version.h`, `include/rogue/Logging.h`, `include/rogue/hardware/MemMap.h`, `include/rogue/hardware/axi/AxiMemMap.h`, `include/rogue/hardware/axi/AxiStreamDma.h`, `include/rogue/utilities/StreamZip.h`, `include/rogue/utilities/StreamUnZip.h`, `include/rogue/utilities/fileio/StreamReader.h`, `include/rogue/utilities/fileio/StreamWriter.h` — reviewed; findings captured via their implementation file entries above or no independent header-level bugs found.
- `include/rogue/EnableSharedFromThis.h` — the `dynamic_pointer_cast` in `shared_from_this()` returns nullptr if the object is not held by any `shared_ptr` (i.e., called on a stack-allocated instance or before `make_shared`); this is the standard `enable_shared_from_this` precondition and is not a new finding, but callers must observe it.
- **Cross-ref plan 06 (GilRelease call-site audit):** `AxiStreamDma` line 184, `AxiMemMap::doTransaction`, `MemMap::doTransaction`, `Bsp` methods (all Boost.Python entry points lacking `ScopedGil`). Plan 06 is authoritative for the GilRelease appendix table.
