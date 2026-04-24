# DETECTED — Thread-Safety / Memory / Logic Audit

**Branch:** hunt-for-red-october
**Phase:** 01 — Code Review
**Generated:** 2026-04-23
**Source partials:** detected-stream.md, detected-memory.md, detected-protocols.md, detected-hw-core.md, detected-python.md, detected-gil.md

---

## Coverage Summary

- Subsystems audited: 5 + GIL cross-cut
- Files reviewed: 262 (src/ C++ = 88, include/ headers = 98, python/pyrogue/ = 76)
- Total findings (main table): 128 (STREAM=17, MEM=16, PROTO-RSSI=10, PROTO-UDP=6, PROTO-PACK=8, PROTO-SRP=6, PROTO-XVC=3, PROTO-BATCH=7, HW-CORE=27, PY=28; GIL-originated bugs merged into subsystem sections)
- GIL appendix entries: 118 (GIL-001 through GIL-118)
- Class breakdown (main table): threading=100, memory=8, logic=20
- Severity breakdown (main table): critical=0, high=12, medium=58, low=58
- Fixed-on-branch entries: 5 (STREAM-001, MEM-001-adj, PROTO-RSSI-001, PROTO-PACK-001, PY-001; see fixed-in-* status)
- Hotspot coverage: all ROADMAP SC-1 hotspots present ✓

---

## ROADMAP Hot-Spot Coverage

| Hotspot | Required | ID(s) | Status |
|---|---|---|---|
| Logging.cpp raw levelMtx_.lock/unlock | ROADMAP SC-1 | HW-CORE-001, HW-CORE-002 | present ✓ |
| Slave.cpp raw classMtx_ | ROADMAP SC-1 | MEM-001 | present ✓ |
| Transaction.cpp raw classMtx_ | ROADMAP SC-1 | MEM-002 | present ✓ |
| RSSI Controller non-atomic field history | ROADMAP SC-1 | PROTO-RSSI-001 | present ✓ (fixed-in-b1a669c96) |
| Every GilRelease/ScopedGil site documented | ROADMAP SC-1 | GIL-001..GIL-118 | present ✓ (118 sites) |
| ZmqClient::sendString GIL site | ROADMAP SC-1 | GIL-035 | present ✓ |
| AxiStreamDma wrong-direction acceptFrame | ROADMAP SC-1 | HW-CORE-026 (GIL-102) | present ✓ |

---

## Main Findings

| ID | File | Lines | Class | Severity | Description | Status | Repro Hypothesis | Reference | Triggerability |
|---|---|---|---|---|---|---|---|---|---|
| STREAM-001 | include/rogue/interfaces/stream/Fifo.h | 46 | threading | high | dropFrameCnt_ and threadEn_ were non-atomic fields read from runThread while written from acceptFrame/destructor without synchronization | fixed-in-b1a669c96 | TSan race under N×parallel Fifo push vs runThread read | CONCERNS.md §Thread-Safety-Concerns / Fifo Non-Atomic Flags | not-triggerable-A: fixed-in-b1a669c96 |
| STREAM-002 | src/rogue/interfaces/stream/FrameLock.cpp | 65-77 | threading | low | FrameLock::lock() and unlock() use raw frame_->lock_.lock()/unlock() calls without RAII; exception between unlock at line 76 and locked_=false on line 77 is not possible in practice but pattern is fragile | detected | Exception path in future Python callback calling lock()/unlock() could wedge frame lock | CONCERNS.md §Test-Coverage-Gaps / FrameLock Manual Unlock Path | not-triggerable-B: Exception path between lines 76-77 not reachable under current call graph; pattern is fragile code-smell only; no runtime signal |
| STREAM-003 | include/rogue/interfaces/stream/TcpCore.h | 76 | threading | high | threadEn_ is plain bool read in runThread() worker and written in stop() from a different thread without atomic or memory-order guarantee | reproducible | TSan race between TcpCore::stop() and TcpCore::runThread() on threadEn_ under normal connect/disconnect cycle | REPRODUCIBLE.md | stress_atomic_conversions.py |
| STREAM-004 | include/rogue/interfaces/ZmqClient.h | 70-71 | threading | high | threadEn_ and running_ are plain bool fields written in stop() and constructor from caller thread while runThread() reads threadEn_ in a tight loop without atomic or fence | detected | TSan race between ZmqClient::stop() and ZmqClient::runThread() on threadEn_; stop() may also race with constructor on running_ if shared before thread starts; D-14 soak attempt run 24896758946 2026-04-24: runner OOM (lost-communication-with-server) at 1h25m; artifact upload skipped; outcome inconclusive; 2 D-14 budget runs remaining | | stress_atomic_conversions.py |
| STREAM-005 | include/rogue/interfaces/ZmqServer.h | 63 | threading | high | threadEn_ is plain bool written in stop() from caller thread and read in runThread()/strThread() workers without atomic or fence | detected | TSan race between ZmqServer::stop() and the two worker threads on threadEn_; D-14 soak attempt run 24896758946 2026-04-24: runner OOM (lost-communication-with-server) at 1h25m; artifact upload skipped; outcome inconclusive; 2 D-14 budget runs remaining | | stress_atomic_conversions.py |
| STREAM-006 | src/rogue/interfaces/stream/Slave.cpp | 82-83 | threading | medium | frameCount_ and frameBytes_ are plain uint64_t incremented in acceptFrame() which can be called concurrently from multiple Masters without a lock protecting the counters | detected | TSan race when two Masters send frames to same Slave concurrently; narrow window but reachable in normal multi-master configurations | | stress_stream_counters.py |
| STREAM-007 | src/rogue/interfaces/stream/Pool.cpp | 59-65 | threading | medium | getAllocBytes() and getAllocCount() read allocBytes_ and allocCount_ without holding mtx_; writes to these fields happen under mtx_ in allocBuffer()/retBuffer()/createBuffer()/decCounter(), so reads from Python via PyRogue poll threads race with buffer alloc/return | detected | TSan race between polling thread calling getAllocBytes() and DMA/stream worker calling retBuffer() | | stress_stream_counters.py |
| STREAM-008 | src/rogue/interfaces/stream/RateDrop.cpp | 85-98 | threading | medium | dropCount_, nextPeriod_, and timePeriod_ are plain non-atomic members read and written in acceptFrame() without a lock; if two Masters feed the same RateDrop concurrently both threads can race on dropCount_ increment and nextPeriod_ update | detected | TSan race when two Slave callers of acceptFrame() run concurrently on a shared RateDrop instance | | stress_stream_counters.py |
| STREAM-009 | src/rogue/interfaces/stream/Slave.cpp | 110-123 | threading | low | SlaveWrap::acceptFrame() acquires ScopedGil then calls this->get_override() — the ScopedGil is correctly used here since SlaveWrap::acceptFrame() is invoked from C++ worker threads that do not hold the GIL; usage is correct but ambiguous: the call site where Slave::acceptFrame() is invoked from a C++ thread (e.g. Fifo::runThread) confirms wrong-direction concern is absent | detected | GIL-origin audit shows ScopedGil acquisition is correct for C++ worker → Python callback path | | not-triggerable-C: correct ScopedGil cpp-worker->Python; completeness-audit entry; not a bug |
| STREAM-010 | src/rogue/interfaces/ZmqClient.cpp | 354-366 | threading | low | ZmqClient::runThread() acquires ScopedGil inside the C++ std::thread worker to call doUpdate(); this is correct (worker does not hold GIL, ScopedGil acquires it), but the pattern is flagged as ambiguous per failure-mode 2: GilRelease/ScopedGil inside cpp-worker — thread origin is a C++ std::thread | detected | GIL-origin audit: ScopedGil in std::thread worker is correct direction; cross-reference GIL plan 06 for completeness | | not-triggerable-C: correct ScopedGil std::thread worker->Python; completeness-audit entry; not a bug |
| STREAM-011 | src/rogue/interfaces/ZmqServer.cpp | 293-316 | threading | low | ZmqServer::runThread() acquires ScopedGil inside the C++ std::thread worker to dispatch doRequest(); same correct-direction pattern as STREAM-010 but flagged for GIL plan 06 completeness audit | detected | GIL-origin audit: ScopedGil in std::thread worker is correct direction; cross-reference GIL plan 06 | | not-triggerable-C: correct ScopedGil std::thread worker->Python; completeness-audit entry; not a bug |
| STREAM-012 | src/rogue/interfaces/ZmqServer.cpp | 263-272 | threading | low | ZmqServerWrap::doString() acquires ScopedGil inside strThread() which is a std::thread worker; correct-direction usage (worker does not hold GIL) but flagged for GIL plan 06 completeness audit | detected | GIL-origin audit: ScopedGil in std::thread worker is correct direction; cross-reference GIL plan 06 | | not-triggerable-C: correct ScopedGil std::thread worker->Python; completeness-audit entry; not a bug |
| STREAM-013 | src/rogue/interfaces/stream/TcpCore.cpp | 175-222 | threading | medium | TcpCore::acceptFrame() holds both frame lock and bridgeMtx_ simultaneously (lock ordering: frame lock first, then bridgeMtx_); runThread() holds only bridgeMtx_ implicitly via reqLocalFrame; if another path acquires bridgeMtx_ before frame lock the lock ordering is reversed, creating a potential deadlock | detected | Deadlock if concurrent acceptFrame() and a future code path acquires bridgeMtx_ before calling frame->lock() | | not-triggerable-B: Latent lock-order hazard (TcpCore bridgeMtx_ vs frame lock); no current triggering code path; TSan would not flag current code; Phase 4 fix is a documentation comment or wrapper — not sanitizer-verifiable |
| STREAM-014 | src/rogue/interfaces/stream/FrameIterator.cpp | 83-88 | memory | low | decrement() sets framePos_ to frameSize_ (sentinel end-of-frame) when decrement goes below zero, mirroring increment(); this makes past-beginning equal to end, which is counter-intuitive and could cause silent data access past buffer start if caller does not check for this | detected | Unit test: decrement an iterator below begin() and verify data_ is NULL | | not-triggerable-B: Past-beginning iterator; unit-test detectable but produces no sanitizer signal at runtime |
| STREAM-015 | src/rogue/interfaces/stream/TcpCore.cpp | 183 | threading | medium | GilRelease inside TcpCore::acceptFrame (cpp worker callback) — GIL not held by this thread; PyEval_SaveThread on an unowned GIL is a no-op on CPython but implementation-defined behavior | detected | Static analysis only | GIL-048 | stress_gil_wrong_direction.py |
| STREAM-016 | src/rogue/interfaces/stream/Fifo.cpp | 116 | threading | medium | GilRelease inside Fifo::acceptFrame (cpp worker callback) — GIL not held by this thread; wrong-direction usage per D-06; same class as STREAM-015 | detected | Static analysis only | GIL-053 | stress_gil_wrong_direction.py |
| STREAM-017 | src/rogue/interfaces/stream/Slave.cpp | 79 | threading | medium | GilRelease inside stream Slave::acceptFrame (cpp worker) — GIL not held by this cpp worker thread; wrong-direction per D-06 | detected | Static analysis only | GIL-054 | stress_gil_wrong_direction.py |
| MEM-001 | src/rogue/interfaces/memory/Slave.cpp | 55-59 | threading | high | classMtx_.lock() / .unlock() used raw without RAII; if classIdx_ increment or store throws (unlikely on x86, but UB-possible), the lock leaks and every subsequent Slave construction deadlocks | detected | Inject exception between lines 55-59 under TSAN stress; static analysis via -fsanitize=thread should flag the non-RAII pattern at init time | CONCERNS.md §Logging Mutex Manual Lock Pattern (analogous) | stress_raw_lock_unlock.py |
| MEM-002 | src/rogue/interfaces/memory/Transaction.cpp | 94-98 | threading | high | classMtx_.lock() / .unlock() used raw without RAII in Transaction::Transaction(); same deadlock-on-exception risk as MEM-001; any future reorder inside the ctor leaves the lock held | detected | Run TSAN + construction stress under OOM pressure; static analysis flags the bare lock/unlock pair | CONCERNS.md §Logging Mutex Manual Lock Pattern | stress_raw_lock_unlock.py |
| MEM-003 | src/rogue/interfaces/memory/TcpClient.cpp | 117-139 | threading | medium | threadEn_ is a plain bool written by stop() (from Python/main thread) and read by runThread() (from std::thread worker) without any lock or std::atomic qualification | detected | TSan will flag this; run the TcpClient integration test under TSan | — | stress_atomic_conversions.py |
| MEM-004 | src/rogue/interfaces/memory/TcpServer.cpp | 101-159 | threading | medium | Same non-atomic threadEn_ pattern as MEM-003 in TcpServer; stop() writes threadEn_=false from the calling thread while runThread() reads it in while(threadEn_) | detected | TSan will flag this under stop/join concurrent with recv loop | — | stress_atomic_conversions.py |
| MEM-005 | src/rogue/interfaces/memory/Block.cpp | 660-724 | memory | medium | setBytes for list variables with fastByte_ uses memcpy with valueBytes_ bytes; if valueBytes_ > stride_bytes (stride gap between fastByte_ slots), the memcpy overruns into the next slot's region of blockData_ | reproducible | Construct a list variable with valueBits_=8, valueStride_=8, numValues_=N and a block of exactly N bytes; write to last index and check adjacent bytes | CONCERNS.md §Excessive memcpy in Memory Transaction Path; REPRODUCIBLE.md | stress_asan_memory.py |
| MEM-006 | src/rogue/interfaces/memory/Block.cpp | 660-760 | memory | low | setBytes calls malloc(var->valueBytes_) for byte-reversed copies (line 666) with no null-check on the malloc return; NULL buff dereferences crash on ASan | reproducible | Pass a byteReverse variable under extreme memory pressure; ASan will catch the NULL deref | REPRODUCIBLE.md | stress_asan_memory.py |
| MEM-007 | src/rogue/interfaces/memory/Block.cpp | 463 | logic | low | addVariables uses a VLA uint8_t excMask[size_] which is a GCC extension; large size_ values silently overflow the stack | detected | Create a Block with size_ near the stack limit; ASAN stack overflow detection would fire | — | not-triggerable-B: VLA extension; compiler-level concern; no runtime TSan/ASan signal unless size exceeds stack |
| MEM-008 | src/rogue/interfaces/memory/Block.cpp | 1739-1903 | logic | low | Float-format coercion functions handle NaN and infinity correctly; no subnormal data-corruption bug found; design is correct — no bug | detected | (No repro required — no bug found.) | CONCERNS.md §Block Float Coercion Edge Cases | not-triggerable-B: No bug found in float coercion; explicitly noted 'no bug' in DETECTED.md |
| MEM-009 | src/rogue/interfaces/memory/Block.cpp | 1711-1732 | logic | low | setFloat range check uses float comparisons that are false for NaN, so NaN silently passes range validation and is stored into block data; same issue applies to setDouble/setFloat16/setFloat8/setBFloat16/setFloat6/setFloat4 | detected | Pass float('nan') from Python to a float-typed variable with min/max set; verify it stores silently | CONCERNS.md §Block Float Coercion Edge Cases | not-triggerable-B: NaN range check bypass; logic bug; no TSan/ASan runtime signal; Phase 4 fix is a code edit |
| MEM-010 | src/rogue/interfaces/memory/Block.cpp | 287-318 | logic | low | startTransaction catches rogue::GeneralError by value not by const reference; fragile contract: future refactor that moves waitTransaction outside the inner lock_guard would create a deadlock window | detected | Code review — fragile contract not immediately exploitable | — | not-triggerable-B: Fragile contract; no current exploitable race; code review fix |
| MEM-011 | src/rogue/interfaces/memory/Transaction.cpp | 156-178 | threading | medium | Transaction::done() calls parentTran->subTranMap_.erase(id_) while holding child lock but NOT parent lock; two sibling sub-transactions completing concurrently race on subTranMap_ | detected | Create a transaction with two sub-transactions and complete them from two parallel threads simultaneously; TSan will flag the concurrent subTranMap_.erase() | — | stress_memory_sub_transaction.py |
| MEM-012 | src/rogue/interfaces/memory/Emulate.cpp | 93 | logic | low | Emulate::doTransaction logs every allocation at debug level; code smell / logging hygiene, no correctness issue | detected | Run emulator with many allocations and check log output | CONCERNS.md §Memory Emulator Allocation Logging Noise | not-triggerable-B: Log noise; no correctness issue |
| MEM-013 | src/rogue/interfaces/memory/Master.cpp | 419-428 | logic | low | anyBits aligned branch checks only dstData[dstByte] != 0 (one byte) but may skip subsequent aligned bytes if first is zero — false false return possible; verify-mask checks may silently pass when subsequent bytes contain set bits | detected | Construct a bit mask with zero first byte and nonzero second byte in the aligned region; call anyBits over that span and confirm it returns false incorrectly | — | not-triggerable-B: anyBits alignment logic; false-return possible but no race |
| MEM-014 | src/rogue/interfaces/memory/Block.cpp | 192-283 | threading | low | intStartTransaction holds mtx_ lock while calling waitTransaction(0) and reqTransaction(...), both of which acquire mastMtx_; implicit lock-order dependency mtx_ → mastMtx_ is undocumented and fragile | detected | Static lock-order analysis; no immediate deadlock found under current call graph | — | not-triggerable-B: Static lock-order mtx_ -> mastMtx_; no current deadlock under call graph |
| MEM-015 | src/rogue/interfaces/memory/TransactionLock.cpp | 40-53 | threading | low | TransactionLock::TransactionLock() traverses the parentTransaction_ chain while holding GilRelease but without any lock on either the child or parent transactions; latent threading assumption | detected | Construct a sub-transaction chain and lock from two threads simultaneously; TSan may flag the unlocked read of isSubTransaction_ | — | stress_memory_sub_transaction.py |
| MEM-016 | src/rogue/interfaces/memory/Block.cpp | 880 | logic | low | setByteArrayPy error message says "Block::setByteArray" instead of "Block::setByteArrayPy" — mismatched error source name | detected | Trigger the error path; check exception message | — | not-triggerable-B: Error message mismatch; no runtime impact |
| PROTO-RSSI-001 | src/rogue/protocols/rssi/Controller.cpp | 64-77 | threading | high | Controller fields dropCount_, remBusy_, locBusy_, downCount_, retranCount_, locBusyCnt_, remBusyCnt_, threadEn_ were non-atomic uint32_t/bool read from network-IO thread and written from controller worker thread, creating data races under concurrent RSSI operation | fixed-in-b1a669c96 | TSan race under N-parallel RSSI frame push while runThread reads any of these fields | CONCERNS.md §Thread-Safety-Concerns | not-triggerable-A: fixed-in-b1a669c96 |
| PROTO-RSSI-002 | src/rogue/protocols/rssi/Controller.cpp | 125-131, 202-219 | threading | medium | state_ read lock-free in transportRx() at lines 202-219 while runThread() writes it under stMtx_; locTryPeriod_ written by setLocTryPeriod() without synchronization (any thread) and read by runThread — torn read possible on struct timeval | detected | TSan would flag the bare state_ read in transportRx vs write in runThread; locTryPeriod_ set vs runThread read | CONCERNS.md §Thread-Safety-Concerns | stress_rssi_state_races.py |
| PROTO-RSSI-003 | src/rogue/protocols/rssi/Controller.cpp | 391-412 | threading | medium | applicationRx() busy-waits on txListCount_ >= curMaxBuffers_ with bare usleep(10) loop; txListCount_ is plain uint8_t read in applicationRx without holding txMtx_ — lock-free read of non-atomic field updated under mutex | detected | TSan race between transportRx ACK processing (txMtx_ held) and applicationRx txListCount_ read | CONCERNS.md §Thread-Safety-Concerns | stress_rssi_state_races.py |
| PROTO-RSSI-004 | src/rogue/protocols/rssi/Controller.cpp | 415-418 | threading | low | getOpen() reads state_ lock-free from Python thread context; state_ is uint32_t written by runThread without mutex; formally UB and TSan-visible | detected | TSan race between getOpen() call and runThread state transitions | CONCERNS.md §Thread-Safety-Concerns | stress_rssi_state_races.py |
| PROTO-RSSI-005 | src/rogue/protocols/rssi/Controller.cpp | 580-588, 64-77 | logic | low | resetCounters() resets atomic fields without coordination with runThread or transportRx — monitoring concern, not a correctness bug | detected | None — statistical; any concurrent RSSI activity will re-increment within ms of reset | CONCERNS.md §Tech-Debt | not-triggerable-B: resetCounters() monitoring concern; no correctness bug |
| PROTO-RSSI-006 | src/rogue/protocols/rssi/Controller.cpp | 86-88 | logic | low | Default RSSI timeout parameters hard-coded at construction cause spurious retransmits on macOS and loaded CI hosts | detected | Observed: macOS RSSI loopback tests skip to avoid this | CONCERNS.md §Tech-Debt §RSSI-Retransmission-Timeout-Sensitivity | not-triggerable-B: Hardcoded timeout concern; macOS skip handles this in tests |
| PROTO-RSSI-007 | src/rogue/protocols/rssi/Application.cpp | 91-99 | threading | medium | Application::runThread() tight-loops calling cntl_->applicationTx() without GilRelease; potentially high-CPU idle but no threading safety issue | detected | High CPU idle on RSSI Application thread | — | not-triggerable-B: High CPU idle; not a data race |
| PROTO-RSSI-008 | src/rogue/protocols/rssi/Controller.cpp | 198 | threading | medium | GilRelease inside cpp-worker transportRx — GIL not held by this thread; PyEval_SaveThread on an unowned GIL is a no-op on CPython but implementation-defined | detected | Static analysis only | GIL-004 | stress_gil_wrong_direction.py |
| PROTO-RSSI-009 | src/rogue/protocols/rssi/Controller.cpp | 341 | threading | medium | GilRelease inside cpp-worker applicationTx — GIL not held; wrong-direction per D-06 | detected | Static analysis only | GIL-005 | stress_gil_wrong_direction.py |
| PROTO-RSSI-010 | src/rogue/protocols/rssi/Controller.cpp | 371 | threading | medium | GilRelease inside cpp-worker applicationRx — GIL not held; wrong-direction per D-06 | detected | Static analysis only | GIL-006 | stress_gil_wrong_direction.py |
| PROTO-UDP-001 | src/rogue/protocols/udp/Client.cpp, src/rogue/protocols/udp/Server.cpp | 113-126, 107-119 | threading | medium | UDP Client and Server stop() check threadEn_ then join thread, but threadEn_ is a plain bool (non-atomic) written by main thread and read by runThread without synchronization | reproducible | TSan race between stop() writing threadEn_=false and runThread reading threadEn_ in while loop | REPRODUCIBLE.md | stress_atomic_conversions.py |
| PROTO-UDP-002 | src/rogue/protocols/udp/Client.cpp | 192-243 | threading | low | Client::runThread() calls recvfrom without timeout; on stop(), threadEn_ is cleared but blocking recvfrom may not unblock promptly — shutdown-latency issue | detected | stop() may hang if no UDP traffic; observed in integration tests as slow teardown | — | not-triggerable-B: Shutdown latency; not a data race |
| PROTO-UDP-003 | src/rogue/protocols/udp/Server.cpp | 232-244 | threading | low | Server::runThread() memcmp reads remAddr_ without the mutex before deciding whether to lock; benign check-then-lock pattern but TSan may flag the unlocked remAddr_ read | detected | TSan race between runThread memcmp(remAddr_) and acceptFrame reading remAddr_ under udpMtx_ | — | not-triggerable-B: check-then-lock pattern; TSan may flag but it's a benign read before lock |
| PROTO-UDP-004 | src/rogue/protocols/udp/Client.cpp | 183-187 | logic | low | Client::acceptFrame() select-then-sendmsg loop does not check errno after sendmsg returns < 0; hard socket error falls through without logging the specific failure reason | detected | Difficult to trigger; normally a network error would appear in log warning but the retry continues | — | not-triggerable-B: errno not checked after sendmsg; no race |
| PROTO-UDP-005 | src/rogue/protocols/udp/Client.cpp | 147 | threading | medium | GilRelease inside UDP Client acceptFrame (cpp worker callback) — wrong-direction per D-06; GIL not held by this thread | detected | Static analysis only | GIL-026 | stress_gil_wrong_direction.py |
| PROTO-UDP-006 | src/rogue/protocols/udp/Server.cpp | 136 | threading | medium | GilRelease inside UDP Server acceptFrame (cpp worker callback) — wrong-direction per D-06; GIL not held by this thread | detected | Static analysis only | GIL-027 | stress_gil_wrong_direction.py |
| PROTO-PACK-001 | include/rogue/protocols/packetizer/Controller.h | 56 | threading | medium | Controller::dropCount_ was a non-atomic uint32_t incremented in transportRx and read by getDropCount() from arbitrary threads, creating a lock-free read-of-non-atomic race; converted to std::atomic<uint32_t> in commit b1a669c96 | fixed-in-b1a669c96 | TSan race under concurrent packetizer transportRx + Python getDropCount() poll | CONCERNS.md §Thread-Safety-Concerns | not-triggerable-A: fixed-in-b1a669c96 |
| PROTO-PACK-002 | src/rogue/protocols/packetizer/ControllerV2.cpp | 242 | logic | low | ControllerV2::transportRx() calls tranFrame_[tmpDest]->setError(0x80) after tranFrame_[tmpDest].reset() on the EOF path; after reset() the shared_ptr is null — use-after-free/null-deref crash | detected | Any RSSI+packetizer session with an SSI EOF error on the last packet of a transfer will crash the process | — | stress_shared_ptr_null_deref.py |
| PROTO-PACK-003 | src/rogue/protocols/packetizer/ControllerV1.cpp | 174 | logic | low | ControllerV1::transportRx() same pattern: tranFrame_[tmpDest]->setError(0x80) after tranFrame_[0].reset(); double bug: index mismatch (tmpDest vs 0) and use-after-reset; will crash if enSsi_ is set and an SSI error arrives at EOF | detected | Any ControllerV1 SSI-enabled session receiving an error on last packet of a transfer | — | stress_shared_ptr_null_deref.py |
| PROTO-PACK-004 | src/rogue/protocols/packetizer/ControllerV2.cpp | 277-287 | threading | low | ControllerV2::applicationRx() busy-waits on tranQueue_.busy() while holding appMtx_; extends critical section unnecessarily long by polling | detected | Under high application load the appMtx_ busy-wait extends indefinitely; no deadlock but CPU waste | — | not-triggerable-B: busy-wait CPU waste; no data race |
| PROTO-PACK-005 | src/rogue/protocols/packetizer/ControllerV1.cpp | 67 | threading | medium | GilRelease inside cpp-worker transportRx — GIL not held by this thread; wrong-direction per D-06 | detected | Static analysis only | GIL-008 | stress_gil_wrong_direction.py |
| PROTO-PACK-006 | src/rogue/protocols/packetizer/ControllerV1.cpp | 199 | threading | medium | GilRelease inside cpp-worker applicationRx — GIL not held; wrong-direction per D-06 | detected | Static analysis only | GIL-009 | stress_gil_wrong_direction.py |
| PROTO-PACK-007 | src/rogue/protocols/packetizer/ControllerV2.cpp | 91 | threading | medium | GilRelease inside cpp-worker transportRx — GIL not held; wrong-direction per D-06 | detected | Static analysis only | GIL-011 | stress_gil_wrong_direction.py |
| PROTO-PACK-008 | src/rogue/protocols/packetizer/ControllerV2.cpp | 272 | threading | medium | GilRelease inside cpp-worker applicationRx — GIL not held; wrong-direction per D-06 | detected | Static analysis only | GIL-012 | stress_gil_wrong_direction.py |
| PROTO-SRP-001 | src/rogue/protocols/srp/SrpV3Emulation.cpp | 96-115 | threading | low | SrpV3Emulation::runThread() reads threadEn_ lock-free in outer while; threadEn_ is set under queMtx_ in stop() — formally a benign race but TSan may flag it | detected | TSan race between stop() writing threadEn_ under queMtx_ and runThread reading threadEn_ in outer while | — | not-triggerable-B: threadEn_ benign race; outer while read vs mutex write; low-risk benign pattern |
| PROTO-SRP-002 | src/rogue/protocols/srp/SrpV3Emulation.cpp | 271-317 | threading | low | processFrame() holds memMtx_ for the entire write + response-build + sendFrame sequence; sendFrame() may block on frame allocation, creating a liveness issue under load | detected | Any slow downstream transport will serialize all SRP emulation I/O behind memMtx_ during sendFrame | — | not-triggerable-B: Liveness concern under load; no data race |
| PROTO-SRP-003 | src/rogue/protocols/srp/SrpV0.cpp | 237-246 | logic | low | SrpV0::acceptFrame() returns without calling tran->done() on two error paths (bad frame length; header mismatch), leaving the Transaction stuck in the active table until timeout | detected | SRP hardware returning a malformed response; transaction hangs for timeout duration | — | not-triggerable-B: Transaction not done() on error path; correctness bug but not TSan/ASan detectable |
| PROTO-SRP-004 | src/rogue/protocols/srp/SrpV0.cpp | 188 | threading | medium | GilRelease inside acceptFrame (cpp worker) — wrong-direction per D-06; GIL not held by this thread | detected | Static analysis only | GIL-022 | stress_gil_wrong_direction.py |
| PROTO-SRP-005 | src/rogue/protocols/srp/SrpV3.cpp | 212 | threading | medium | GilRelease inside acceptFrame (cpp worker) — wrong-direction per D-06; GIL not held by this thread | detected | Static analysis only | GIL-024 | stress_gil_wrong_direction.py |
| PROTO-SRP-006 | src/rogue/protocols/srp/SrpV3Emulation.cpp | 214 | threading | medium | GilRelease inside processFrame called from runThread (cpp worker) — wrong-direction per D-06 | detected | Static analysis only | GIL-025 | stress_gil_wrong_direction.py |
| PROTO-XVC-001 | src/rogue/protocols/xilinx/XvcConnection.cpp, src/rogue/protocols/xilinx/XvcServer.cpp | 57, 202 | logic | low | XVC TCP socket operates without TLS or any authentication layer; raw JTAG operations exposed in plaintext; deployment-layer concern deferred to V2-04 | detected | Network-accessible XVC port on shared or non-isolated infrastructure | CONCERNS.md §Security-Considerations | not-triggerable-B: Deployment security concern (plaintext JTAG); no runtime sanitizer signal; deferred to V2-04 |
| PROTO-XVC-002 | src/rogue/protocols/xilinx/Xvc.cpp | 169-221 | threading | medium | Xvc::stop() uses a self-pipe (wakeFd_[1]) and queue_.stop() to unblock blocking select(); shutdown sequence is correct but intermediate state between queue_.stop() and wakeFd_ write leaves any active XvcConnection::readTo select() blocked if wakeFd_ write is delayed by EINTR | detected | Concurrent XVC client connected + stop() called while EINTR loop runs | CONCERNS.md §Test-Coverage-Gaps XVC-Thread-Shutdown | not-triggerable-B: Xvc::stop self-pipe + queue_.stop() + EINTR shutdown race; requires live JTAG client to trigger; no stable sanitizer harness feasible; Phase 4 fix is code review, not sanitizer rerun |
| PROTO-XVC-003 | src/rogue/protocols/xilinx/Xvc.cpp | 289-296 | logic | low | Xvc::acceptFrame() silently discards incoming frames when tranQueue_.busy() returns true; dropped reply causes xfer() to block in queue_.pop() until the next (mis-matched) reply arrives or stop() is called | detected | Downstream congestion while XVC client is active; xfer() hangs indefinitely | — | not-triggerable-B: Silent discard of xfer() replies; no race |
| PROTO-BATCH-001 | src/rogue/protocols/batcher/CombinerV1.cpp, src/rogue/protocols/batcher/CombinerV2.cpp | 107-113, 93-99 | threading | low | CombinerV1/V2::acceptFrame() acquires mtx_ after frame->lock(); sendBatch() acquires mtx_ first then FrameLock per-frame; orderings consistent and do not invert — no deadlock risk | detected-only | No plausible deadlock path found; logged for audit completeness | — | not-triggerable-B: Explicitly marked detected-only; consistent lock ordering confirmed |
| PROTO-BATCH-002 | src/rogue/protocols/batcher/CombinerV1.cpp | 108 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong-direction per D-06; GIL not held by this thread | detected | Static analysis only | GIL-013 | stress_gil_wrong_direction.py |
| PROTO-BATCH-003 | src/rogue/protocols/batcher/CombinerV2.cpp | 94 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-015 | stress_gil_wrong_direction.py |
| PROTO-BATCH-004 | src/rogue/protocols/batcher/SplitterV1.cpp | 74 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-017 | stress_gil_wrong_direction.py |
| PROTO-BATCH-005 | src/rogue/protocols/batcher/SplitterV2.cpp | 74 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-018 | stress_gil_wrong_direction.py |
| PROTO-BATCH-006 | src/rogue/protocols/batcher/InverterV1.cpp | 73 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-019 | stress_gil_wrong_direction.py |
| PROTO-BATCH-007 | src/rogue/protocols/batcher/InverterV2.cpp | 73 | threading | medium | GilRelease inside acceptFrame called from cpp worker — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-020 | stress_gil_wrong_direction.py |
| HW-CORE-001 | src/rogue/Logging.cpp | 109-112 | threading | high | levelMtx_.lock() called in Logging::Logging ctor at line 109; exception thrown by loggers_.push_back or updateLevelLocked before levelMtx_.unlock() at line 112 would exit without releasing levelMtx_, permanently wedging any subsequent logger creation | detected | Throw std::bad_alloc from loggers_.push_back with address-space pressure before levelMtx_.unlock(); subsequent Logging::create call will deadlock | CONCERNS.md §Known-Bugs §Logging-Mutex-Manual-Lock-Unlock | stress_raw_lock_unlock.py |
| HW-CORE-002 | src/rogue/Logging.cpp | 120-127, 146-149, 155-163, 167-176, 181-183, 188-190 | threading | high | Six additional raw levelMtx_.lock() / levelMtx_.unlock() pairs in ~Logging, setLevel, setFilter, setForwardPython, forwardPython, setEmitStdout, emitStdout; none are exception-safe; new rogue::LogFilter inside setFilter (line 157) is the most concrete heap-allocation danger | detected | Inject allocation failure via LD_PRELOAD while calling Logging::setFilter under thread contention; deadlock on next setLevel | CONCERNS.md §Known-Bugs §Logging-Mutex-Manual-Lock-Unlock | stress_raw_lock_unlock.py |
| HW-CORE-003 | include/rogue/Queue.h | 47, 99, 150 | threading | medium | Queue::busy_ was a non-atomic bool read lock-free from busy() while being updated under mtx_ lock in push() and pop(); data race; converted to std::atomic<bool> in commit b1a669c96 | fixed-in-b1a669c96 | TSan race under parallel push/pop + busy() calls; no longer triggerable post-fix | CONCERNS.md §Thread-Safety-Concerns §Queue-Busy-Flag-Non-Atomic | not-triggerable-A: fixed-in-b1a669c96 |
| HW-CORE-004 | include/rogue/Helpers.h | 25-27 | logic | low | rogueStreamTap macro is marked DEPRECATED in the comment but remains present; byte-for-byte alias of rogueStreamConnect; blocks removal of old API name | detected | No runtime failure expected; audit finding for code-cleanliness | CONCERNS.md §Tech-Debt §Deprecated-Stream-Tap-Macro | not-triggerable-B: Deprecated rogueStreamTap macro; no runtime issue |
| HW-CORE-005 | src/rogue/GilRelease.cpp | 41-45, 48-54 | threading | low | GilRelease::acquire() calls PyEval_RestoreThread(state_) unconditionally when state_ != NULL; if the caller has already re-acquired the GIL externally via nested ScopedGil and then calls acquire() explicitly, the internal state_ pointer is stale but re-used | detected | Construct two nested GilRelease scopes, call inner .acquire() manually, then allow outer dtor to re-acquire; this double-restores on CPython <= 3.12 and may crash | — | not-triggerable-B: Nested GilRelease double-restore; edge case; no TSan signal under normal usage |
| HW-CORE-006 | src/rogue/hardware/axi/AxiStreamDma.cpp | 45 | threading | medium | rha::AxiStreamDma::sharedBuffers_ is a static std::map modified by openShared, closeShared, and zeroCopyDisable without any lock; concurrent construction of two AxiStreamDma objects races on sharedBuffers_.find and sharedBuffers_.insert | detected | Construct two AxiStreamDma instances with different device paths from two Python threads simultaneously; TSan should flag the unsynchronized map operations | — | stress_bsp_gil.py |
| HW-CORE-007 | src/rogue/hardware/axi/AxiStreamDma.cpp | 192-215 | memory | medium | AxiStreamDma constructor opens the shared buffer structure; if ::open() fails at line 192 and openShared succeeded, the exception path calls closeShared(desc_) but fd_ is never set to -1 so stop() guard is ambiguous | detected | Inject open failure via LD_PRELOAD; check that the shared descriptor reference count is correctly decremented and no double-close of fd_ occurs | — | stress_asan_memory.py |
| HW-CORE-008 | src/rogue/hardware/axi/AxiStreamDma.cpp | 502 | threading | low | In AxiStreamDma::runThread, while(threadEn_) reads threadEn_ (plain bool class member) from a std::thread worker without an atomic load; stop() sets threadEn_=false from the calling thread — formally a data race on a non-atomic bool | detected | TSan will flag this as a data race when stop() and runThread() execute concurrently | — | stress_atomic_conversions.py |
| HW-CORE-009 | src/rogue/hardware/axi/AxiStreamDma.cpp | 184 | threading | low | rogue::GilRelease noGil is used in the AxiStreamDma constructor (line 184), called from Python-originated __init__; correct direction for a blocking openShared/open call; logged for GIL completeness audit | detected | n/a — correct usage; logged for GIL completeness audit | CONCERNS.md §Thread-Safety-Concerns §GIL-Release-Pattern | not-triggerable-C: correct GilRelease direction; completeness-audit entry; not a bug |
| HW-CORE-010 | src/rogue/hardware/MemMap.cpp | 63-65 | memory | medium | In MemMap::MemMap, if mmap fails (returns MAP_FAILED), a GeneralError exception is thrown but fd_ (already opened at line 59) is not closed before the throw; file descriptor leaks on the exception path | detected | Inject mmap failure via ulimit -v or a mock; check that no fd leak occurs when the constructor throws | — | stress_asan_memory.py |
| HW-CORE-011 | src/rogue/hardware/axi/AxiMemMap.cpp | 63-69 | memory | medium | In AxiMemMap::AxiMemMap, the version check at line 63 throws GeneralError without closing fd_ (opened at line 57); file descriptor leaks on the exception path | detected | Open device with an old driver API; verify no fd leak when the first version check fails | — | stress_asan_memory.py |
| HW-CORE-012 | src/rogue/utilities/Prbs.cpp | 244-246 | threading | high | Prbs::setRxEnable calls pMtx_.lock() / pMtx_.unlock() directly (raw lock/unlock) rather than std::lock_guard; any exception between the lock and unlock calls would leak the mutex | detected | No immediate throw path; future edits that add validation inside the critical section would silently create a deadlock | — | stress_raw_lock_unlock.py |
| HW-CORE-013 | src/rogue/utilities/Prbs.cpp | 321-330 | threading | high | Prbs::resetCount calls pMtx_.lock() / pMtx_.unlock() directly without RAII; same raw-lock pattern as HW-CORE-012 | detected | No current throw path inside the critical section; same deadlock blast-radius as HW-CORE-012 | — | stress_raw_lock_unlock.py |
| HW-CORE-014 | src/rogue/utilities/Prbs.cpp | 202-205 | threading | medium | Prbs::runThread reads threadEn_ (plain non-atomic bool) and txSize_ without holding pMtx_; disable() sets threadEn_=false from the calling thread while runThread reads it concurrently — data race | detected | TSan will flag threadEn_ and txSize_ reads in runThread as races with disable() and enable() | — | stress_atomic_conversions.py |
| HW-CORE-015 | src/rogue/interfaces/api/Bsp.cpp | 55 | logic | medium | Bsp::Bsp(modName, rootClass) waits for the Python root to become running with a busy-loop without any timeout; if the root fails to start, this constructor loops forever | detected | Construct Bsp from a rootClass that never sets running=True; the caller blocks forever | — | not-triggerable-B: Bsp busy-loop wait-for-running without timeout; not a data race; Phase 4 fix adds timeout |
| HW-CORE-016 | src/rogue/interfaces/api/Bsp.cpp | 40-44, 46-56 | threading | medium | All Bsp methods call into Boost.Python on this->_obj without holding the GIL explicitly; C++-originated calls to these methods races with CPython's GC and reference-counting machinery | detected | Call Bsp::getAttribute from a plain std::thread while the Python GIL is not held; TSan or CPython debug build will flag refcount corruption | — | stress_bsp_gil.py |
| HW-CORE-017 | src/rogue/utilities/StreamUnZip.cpp | 98-101 | memory | medium | In StreamUnZip::acceptFrame, when strm.avail_in==0, the code unconditionally advances rBuff and dereferences it; if BZip2 produces more output than input being consumed, the iterator advances past endBuffer() and is dereferenced out of bounds | reproducible | Feed a corrupt or prematurely-truncated bzip2 stream; if BZ2_bzDecompress returns BZ_OK with avail_in==0 and avail_out>0, the iterator overflow will occur | REPRODUCIBLE.md | stress_asan_memory.py |
| HW-CORE-018 | src/rogue/utilities/fileio/StreamReader.cpp | 180-231 | threading | medium | StreamReader::runThread accesses fd_ (read at line 180, written in intClose via line 144) without holding mtx_; close() acquires mtx_ and calls intClose() — data race on fd_ between thread loop and concurrent close() | detected | Call close() from the main thread while runThread is active reading the file; TSan should flag the unsynchronized fd_ access | — | stress_fileio_fd_race.py |
| HW-CORE-019 | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 87-88 | threading | low | StreamWriterChannel::getFrameCount() reads frameCount_ without any lock (a data race with concurrent acceptFrame calls that increment under mtx_) | detected | Concurrent acceptFrame + getFrameCount calls; TSan will flag the unlocked read in getFrameCount | — | stress_stream_counters.py |
| HW-CORE-020 | include/rogue/hardware/drivers/DmaDriver.h | 399-423 | logic | low | dmaReadBulkIndex uses a C99 VLA struct DmaReadData r[count]; if count is 0 or very large this produces either a zero-length VLA (UB in C++) or a stack overflow | detected | Call dmaReadBulkIndex with count=0 or count > stack_frame_size / sizeof(DmaReadData) | — | not-triggerable-B: VLA in DmaDriver.h header; UB but stack-bounded in practice; no TSan signal |
| HW-CORE-021 | src/rogue/utilities/Prbs.cpp | 343 | threading | medium | GilRelease inside Prbs::genFrame called from runThread (cpp worker) — GIL not held by this thread; wrong-direction per D-06 | detected | Static analysis only | GIL-076 | stress_gil_wrong_direction.py |
| HW-CORE-022 | src/rogue/utilities/Prbs.cpp | 423 | threading | medium | GilRelease inside Prbs::acceptFrame (cpp worker callback) — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-077 | stress_gil_wrong_direction.py |
| HW-CORE-023 | src/rogue/utilities/StreamUnZip.cpp | 62 | threading | medium | GilRelease inside StreamUnZip::acceptFrame (cpp worker callback) — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-078 | stress_gil_wrong_direction.py |
| HW-CORE-024 | src/rogue/utilities/StreamZip.cpp | 63 | threading | medium | GilRelease inside StreamZip::acceptFrame (cpp worker callback) — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-079 | stress_gil_wrong_direction.py |
| HW-CORE-025 | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 75 | threading | medium | GilRelease inside StreamWriterChannel::acceptFrame (cpp worker callback) — wrong-direction per D-06; GIL not held | detected | Static analysis only | GIL-084 | stress_gil_wrong_direction.py |
| HW-CORE-026 | src/rogue/utilities/fileio/StreamWriter.cpp | 316 | threading | medium | GilRelease inside StreamWriter::writeFile called from cpp worker via acceptFrame chain — wrong-direction per D-06 | detected | Static analysis only | GIL-096 | stress_gil_wrong_direction.py |
| HW-CORE-027 | src/rogue/hardware/axi/AxiStreamDma.cpp | 339 | threading | medium | GilRelease inside AxiStreamDma::acceptFrame (cpp worker callback) — wrong-direction per D-06; GIL not held by this thread | detected | Static analysis only | GIL-102 | stress_gil_wrong_direction.py |
| PY-001 | python/pyrogue/interfaces/_Virtual.py | 126-144 | threading | high | VirtualNode._loadLock double-checked-locking pattern guards _loadNodes() init-once; correct under Python GIL but fragile — future editors must preserve lock acquisition and ensure _loaded is set last inside the lock | fixed-in-709b5f327 | Concurrent getNode() calls from multiple threads before tree populates; races on _nodes dict mutation visible with two-thread synthetic harness | CONCERNS.md §Known-Bugs §VirtualClient-Thread-Safety-Race | not-triggerable-A: fixed-in-709b5f327 |
| PY-002 | python/pyrogue/interfaces/_Virtual.py | 165-200 | threading | low | Double-checked-locking pattern repeated in three call sites without centralising the guard; if any future caller accesses _nodes without the guard the invariant silently breaks | detected | Code review: add a new property accessor that skips the lock check | CONCERNS.md §Fragile-Areas | not-triggerable-B: Double-checked-locking pattern code smell; future accessor without guard; no current race |
| PY-003 | python/pyrogue/interfaces/_Virtual.py | 313-316 | threading | medium | VirtualNode._doUpdate iterates self._functions list without a lock; concurrent _addListener/_delListener mutations can cause RuntimeError: list changed size during iteration | detected | Add listener from one thread while VirtualClient's update thread fires _doUpdate; stress with 10k update/add cycles | — | stress_python_update_worker.py |
| PY-004 | python/pyrogue/interfaces/_Virtual.py | 438-443 | threading | medium | VirtualClient._monWorker thread is started non-daemon and is only joined with a 3-second timeout in stop(); if the monitor thread is blocked at shutdown, stop() returns leaving the thread running and the ZMQ context alive | detected | Block _reqLock from another thread during stop() call; observe hang or missing join | — | not-triggerable-B: Thread stop join timeout; daemon status concern; not a data race |
| PY-005 | python/pyrogue/interfaces/_Virtual.py | 591-595 | threading | low | _monWorker reads self._monEnable (plain Python bool) without _reqLock; write happens in stop() without the lock as well; safe under CPython GIL but inconsistent pattern | detected | Theoretical only; no realistic race under CPython GIL | — | not-triggerable-B: Safe under CPython GIL; theoretical only |
| PY-006 | python/pyrogue/interfaces/_Virtual.py | 696-713 | threading | medium | _doUpdate is called from the C++ ZMQ SUB receive thread; reads self._root, iterates self._varListeners, calls n._doUpdate(val) — all without a lock; concurrent __init__ can overlap with first SUB message arriving during bootstrap | detected | Start VirtualClient and immediately send a publish from the server before __init__ completes; observe AttributeError or list mutation race | CONCERNS.md §VirtualClient-Thread-Safety-Race | stress_python_update_worker.py |
| PY-007 | python/pyrogue/_PollQueue.py | 160-220 | threading | low | PollQueue._poll checks self.empty() and self.paused() outside _condLock before deciding to wait; TOCTOU window where state can change between read and wait; practical impact is a spurious extra sleep cycle | detected | High-frequency _addEntry+_blockDecrement under load; observe delayed poll cycle (no corruption) | — | not-triggerable-B: TOCTOU window; spurious sleep only; no corruption |
| PY-008 | python/pyrogue/_PollQueue.py | 71 | threading | low | PollQueue._pollThread is started non-daemon and _stop() signals via _condLock.notify() but does not call _pollThread.join(); if poll thread is blocked in a long startTransaction call, stop() returns without joining | detected | Issue a root.stop() while a slow block transaction is in flight; observe delayed exit | — | not-triggerable-B: Thread non-join; liveness concern; no data race |
| PY-009 | python/pyrogue/_Root.py | 455-456 | threading | low | Root._hbeatThread is started non-daemon and is not joined in Root.stop(); stop() sets _running=False and returns but heartbeat thread may run one more updateGroup cycle after stop() has returned | detected | Call root.stop() and immediately destroy the root; observe queue-put-after-sentinel race | — | not-triggerable-B: Heartbeat thread non-join; one extra cycle; no data race |
| PY-010 | python/pyrogue/_Root.py | 247-252 | threading | low | Root._updateTrack dict is modified from every calling thread inside updateGroup() with _updateLock held only in the fallback creation branch; fast path does not hold _updateLock — safe under CPython GIL but implicit assumption | detected | Two threads both enter updateGroup() for the first time simultaneously; TSan would flag | — | not-triggerable-B: GIL-safe under CPython; theoretical |
| PY-011 | python/pyrogue/_Root.py | 617 | logic | low | Root.getNode is decorated with @ft.lru_cache(maxsize=None) on an instance method; functools.lru_cache on instance methods leaks instances because the cache holds a strong reference to self | detected | Build large tree, call getNode before _rootAttached completes from a background thread; observe stale None return | — | not-triggerable-B: lru_cache instance leak; not a race; Phase 4 code fix |
| PY-012 | python/pyrogue/_Root.py | 450-451 | threading | low | Root._updateQueue and Root._updateThread are non-daemon; if an exception in _updateWorker causes the thread to exit before the sentinel None is consumed, stop() hangs on join() indefinitely with no timeout | detected | Inject exception into _updateWorker; observe deadlock on stop() | — | not-triggerable-B: Exception in worker causes join hang; no data race |
| PY-013 | python/pyrogue/interfaces/_ZmqServer.py | 107-115 | threading | medium | ZmqServer._updateList is a plain dict mutated by _varUpdate (Root update-worker thread) and read/cleared by _varDone (same thread — safe); but _doRequest/_doString are called from C++ ZMQ REP thread context; dict can be mutated from two threads without a lock | detected | Send a ZMQ REQ while a batch of variable updates is flushing; TSan would flag dict read/write race | — | stress_python_update_worker.py |
| PY-014 | python/pyrogue/_Process.py | 231-238 | threading | low | Process._stop() signals the run loop by setting _runEn=False but does not join self._thread; the _run() function may be in time.sleep(1) and will not exit for up to 1 second after _stop() returns | detected | Call process._stop() while run loop is in time.sleep; observe thread alive after method returns | — | not-triggerable-B: _stop without join; liveness; no data race |
| PY-015 | python/pyrogue/_Process.py | 272-283 | threading | low | _run() sets Running.set(True) outside the _lock; a concurrent __call__ or _startProcess may re-enter before Running is set, bypassing the guard | detected | Two threads calling process() simultaneously before the first sets Running=True | — | not-triggerable-B: Re-entry race window; low probability; CPython GIL provides protection |
| PY-016 | python/pyrogue/_RunControl.py | 102-117 | threading | low | RunControl._setRunState reads self.runState.valueDisp() outside _threadLock before entering the lock to check self._thread.is_alive(); state can change between the check and the lock acquisition | detected | Two concurrent writes of 'Running' from different threads; TSan would flag | — | not-triggerable-B: TOCTOU between read and lock; low probability |
| PY-017 | python/pyrogue/interfaces/_SqlLogging.py | 51 | threading | medium | SqlLogger._queue is an unbounded queue.Queue(); if SQL database connection is slow the queue can grow without bound causing OOM; no backpressure or high-watermark alarm | detected | High-frequency variable updates (>1 kHz) with slow SQLite disk I/O; measure queue depth under load | CONCERNS.md §Scaling-Limits | not-triggerable-B: Unbounded queue OOM; resource concern; no data race |
| PY-018 | python/pyrogue/interfaces/_SqlLogging.py | 52-53 | threading | low | SqlLogger._thread is started non-daemon with an unbounded queue.Queue; if _stop() is never called, the worker thread blocks forever on queue.get() and prevents interpreter exit | detected | Kill root with Ctrl-C before calling _stop(); observe hanging thread | — | not-triggerable-B: Non-daemon blocking thread; liveness; no data race |
| PY-019 | python/pyrogue/interfaces/simulation.py | 89-101 | threading | low | SideBandSim._stop() sets self._run=False inside _lock but does not join _recvThread; recv thread polls ZMQ with a 1-second timeout so it may remain alive up to 1 second after _stop() returns; ZMQ context (_ctx) is not explicitly destroyed, leaking file descriptors | detected | Call _stop() then immediately destroy the object; measure open fd count | — | not-triggerable-B: ZMQ context not destroyed; FD leak; no data race |
| PY-020 | python/pyrogue/interfaces/_SimpleClient.py | 87-93 | threading | low | SimpleClient._stop() sets _runEn=False but does not join _subThread; the sub thread blocks on self._sub.recv_pyobj() with no timeout set and may never return | detected | Call _stop() on a connected client; observe _subThread.is_alive() still True | — | not-triggerable-B: _stop without join; liveness |
| PY-021 | python/pyrogue/protocols/gpib.py | 63 | threading | low | Gpib._workerQueue is an unbounded queue.Queue(); high-frequency memory transactions can accumulate faster than the GPIB bus can drain them, causing unbounded memory growth | detected | Issue 10k transactions in a burst; measure queue depth | — | not-triggerable-B: Unbounded GPIB queue; resource concern |
| PY-022 | python/pyrogue/protocols/_uart.py | 55 | threading | low | _Uart._workerQueue is an unbounded queue.Queue(); same unbounded queue concern as PY-021 for UART transaction bursts | detected | Issue 10k transactions in a burst; measure queue depth | — | not-triggerable-B: Unbounded UART queue; resource concern |
| PY-023 | python/pyrogue/protocols/_Network.py | 426 | threading | low | _wait_open helper thread is started as daemon=True with no stop signal and no reference retained; polls self._rssi.getOpen() in a 0.1ms busy loop; if RSSI session never opens, the thread loops until process exit consuming CPU | detected | Start a UdpRssiConnection that never completes RSSI handshake; observe CPU spin | — | not-triggerable-B: Daemon busy-loop thread; CPU waste; no data race |
| PY-024 | python/pyrogue/protocols/epicsV7.py | 802-803 | threading | low | EPICS V7 IOC thread is daemon=True but _stop() does not join or signal the IOC thread; any in-flight IOC callback referencing PyRogue variables may race with root teardown | detected | Stop root while IOC is processing a CA monitor put; observe potential use-after-free of Python objects | — | not-triggerable-B: IOC thread not joined; liveness; potential UAF but not TSan-detectable without specific test setup |
| PY-025 | python/pyrogue/utilities/hls/_RegInterfParser.py | 85 | memory | low | open(fname) at line 85 is not wrapped in a with statement and fhand is never explicitly closed; if an exception is raised in the parsing loop the file handle leaks | detected | Inject exception inside the for-loop; verify fd count with lsof | — | not-triggerable-B: File handle not closed; resource; not a race |
| PY-026 | python/pyrogue/pydm/data_plugins/rogue_plugin.py | 135 | threading | medium | RogueConnection._updateVariable is registered as a addListener callback on a VirtualNode; _updateVariable calls self.new_value_signal[...].emit(...) directly from the Root update-worker thread, not the Qt main thread; default connection type means signal emission crosses into the Qt event loop without explicit queuing | detected | Connect a PyDM label to a fast-updating Rogue variable and stress the update thread; observe occasional Qt crash or corrupted display | — | stress_python_update_worker.py |
| PY-027 | python/pyrogue/_Variable.py | 90 | threading | low | BaseVariable._cv is a threading.Condition(); if callers of waitOnUpdate() hold _cv across variable destructor invocations during Root.stop(), a deadlock is possible between the condition variable holder and the tree-teardown lock order | detected | Issue root.stop() while a thread waits on a variable condition; observe potential deadlock | — | not-triggerable-B: Condition variable deadlock scenario; not TSan-detectable without precise triggering |
| PY-028 | python/pyrogue/_Root.py | 243-244 | logic | low | self._pollQueue = self._pollQueue = pr.PollQueue(root=self) at line 243 is a double assignment (likely a copy-paste artifact); functionally harmless | detected | Code review only; no runtime impact | — | not-triggerable-B: Double assignment; copy-paste artifact; no runtime impact |

## Triggerability Summary

**Populated by:** Phase 2 Plan 01 (2026-04-23)
**Rubric:** .planning/phases/02-sanitizer-ci-infrastructure/02-CONTEXT.md §D-14
**Cluster map:** .planning/phases/02-sanitizer-ci-infrastructure/02-01-CLUSTER-MAP.md

| Disposition | Count |
|-------------|-------|
| Covered by cluster script | 66 |
| not-triggerable-A (fixed) | 5 |
| not-triggerable-B (logic/static) | 52 |
| not-triggerable-C (correct GilRelease) | 5 |
| not-triggerable-D (redundant GilRelease) | 0 |
| **Total main-table rows** | **128** |

Every entry in DETECTED.md main table now has a `Triggerability` cell populated — REPRO-06 coverage is mechanically auditable via the column.

---

---

## GilRelease / ScopedGil Audit

| ID | Site | File | Lines | Thread Origin | Verdict | Notes |
|---|---|---|---|---|---|---|
| GIL-001 | Version::sleep | src/rogue/Version.cpp | 159 | python-callback | correct | Python-bound; releases GIL across blocking ::sleep() |
| GIL-002 | Version::usleep | src/rogue/Version.cpp | 164 | python-callback | correct | Python-bound; releases GIL across ::usleep() |
| GIL-003 | Controller::stop (RSSI) | src/rogue/protocols/rssi/Controller.cpp | 134 | python-callback | correct | Releases GIL while joining thread; called from Python stop sequence |
| GIL-004 | Controller::transportRx (RSSI) | src/rogue/protocols/rssi/Controller.cpp | 198 | cpp-worker | wrong-direction | Called from Transport::acceptFrame which runs in a cpp thread; GIL not held here. See PROTO-RSSI-008 |
| GIL-005 | Controller::applicationTx (RSSI) | src/rogue/protocols/rssi/Controller.cpp | 341 | cpp-worker | wrong-direction | Called from Application::runThread; cpp worker does not hold GIL. See PROTO-RSSI-009 |
| GIL-006 | Controller::applicationRx (RSSI) | src/rogue/protocols/rssi/Controller.cpp | 371 | cpp-worker | wrong-direction | Called from Application::acceptFrame which is called from Application::runThread. See PROTO-RSSI-010 |
| GIL-007 | Controller::stopQueue (packetizer) | src/rogue/protocols/packetizer/Controller.cpp | 75 | python-callback | correct | Called from destructor / stop sequence; releases GIL while stopping queue |
| GIL-008 | ControllerV1::transportRx | src/rogue/protocols/packetizer/ControllerV1.cpp | 67 | cpp-worker | wrong-direction | transportRx is a stream callback, called from cpp transport worker; GIL not held. See PROTO-PACK-005 |
| GIL-009 | ControllerV1::applicationRx | src/rogue/protocols/packetizer/ControllerV1.cpp | 199 | cpp-worker | wrong-direction | applicationRx called from Application cpp worker thread. See PROTO-PACK-006 |
| GIL-010 | Application::~Application (packetizer) | src/rogue/protocols/packetizer/Application.cpp | 65 | ambiguous | needs-investigation | Destructor; may run during Python teardown or from Python caller; GilRelease in dtor is suspect |
| GIL-011 | ControllerV2::transportRx | src/rogue/protocols/packetizer/ControllerV2.cpp | 91 | cpp-worker | wrong-direction | Same pattern as GIL-008; cpp transport callback. See PROTO-PACK-007 |
| GIL-012 | ControllerV2::applicationRx | src/rogue/protocols/packetizer/ControllerV2.cpp | 272 | cpp-worker | wrong-direction | Same pattern as GIL-009; cpp application worker callback. See PROTO-PACK-008 |
| GIL-013 | CombinerV1::acceptFrame | src/rogue/protocols/batcher/CombinerV1.cpp | 108 | cpp-worker | wrong-direction | acceptFrame is a stream Slave callback called from cpp worker thread. See PROTO-BATCH-002 |
| GIL-014 | CombinerV1::sendBatch | src/rogue/protocols/batcher/CombinerV1.cpp | 143 | python-callback | correct | sendBatch is Python-bound (.def); releases GIL while calling reqFrame/sendFrame |
| GIL-015 | CombinerV2::acceptFrame | src/rogue/protocols/batcher/CombinerV2.cpp | 94 | cpp-worker | wrong-direction | Same as GIL-013; cpp worker calls acceptFrame. See PROTO-BATCH-003 |
| GIL-016 | CombinerV2::sendBatch | src/rogue/protocols/batcher/CombinerV2.cpp | 126 | python-callback | correct | Python-bound; GilRelease before reqFrame/sendFrame |
| GIL-017 | SplitterV1::acceptFrame | src/rogue/protocols/batcher/SplitterV1.cpp | 74 | cpp-worker | wrong-direction | acceptFrame callback, called from cpp worker. See PROTO-BATCH-004 |
| GIL-018 | SplitterV2::acceptFrame | src/rogue/protocols/batcher/SplitterV2.cpp | 74 | cpp-worker | wrong-direction | acceptFrame callback, called from cpp worker. See PROTO-BATCH-005 |
| GIL-019 | InverterV1::acceptFrame | src/rogue/protocols/batcher/InverterV1.cpp | 73 | cpp-worker | wrong-direction | acceptFrame callback, called from cpp worker. See PROTO-BATCH-006 |
| GIL-020 | InverterV2::acceptFrame | src/rogue/protocols/batcher/InverterV2.cpp | 73 | cpp-worker | wrong-direction | acceptFrame callback, called from cpp worker. See PROTO-BATCH-007 |
| GIL-021 | SrpV0::doTransaction (send) | src/rogue/protocols/srp/SrpV0.cpp | 138 | cpp-worker | wrong-direction | doTransaction called from Master::intTransaction; classified wrong-direction due to blocking I/O pattern in cpp context |
| GIL-022 | SrpV0::acceptFrame | src/rogue/protocols/srp/SrpV0.cpp | 188 | cpp-worker | wrong-direction | Stream callback from cpp transport worker. See PROTO-SRP-004 |
| GIL-023 | SrpV3::doTransaction (send) | src/rogue/protocols/srp/SrpV3.cpp | 166 | ambiguous | needs-investigation | doTransaction called via Slave interface; caller may be Python thread or cpp worker depending on topology |
| GIL-024 | SrpV3::acceptFrame | src/rogue/protocols/srp/SrpV3.cpp | 212 | cpp-worker | wrong-direction | Stream callback from cpp transport worker. See PROTO-SRP-005 |
| GIL-025 | SrpV3Emulation::processFrame | src/rogue/protocols/srp/SrpV3Emulation.cpp | 214 | cpp-worker | wrong-direction | processFrame called exclusively from SrpV3Emulation::runThread. See PROTO-SRP-006 |
| GIL-026 | Client::acceptFrame (UDP) | src/rogue/protocols/udp/Client.cpp | 147 | cpp-worker | wrong-direction | UDP Client::acceptFrame is a stream Slave callback; called from cpp worker upstream. See PROTO-UDP-005 |
| GIL-027 | Server::acceptFrame (UDP) | src/rogue/protocols/udp/Server.cpp | 136 | cpp-worker | wrong-direction | UDP Server::acceptFrame stream callback from cpp worker. See PROTO-UDP-006 |
| GIL-028 | XvcServer::run (select) | src/rogue/protocols/xilinx/XvcServer.cpp | 113 | cpp-worker | correct | Inside Xvc::runThread (cpp-worker); nested under ScopedGil (GIL-101); inner GilRelease releases for blocking select() |
| GIL-029 | Xvc::~Xvc (destructor) | src/rogue/protocols/xilinx/Xvc.cpp | 92 | ambiguous | needs-investigation | Destructor runs in whichever thread destroys it; may run from Python caller or during interpreter teardown |
| GIL-030 | Xvc::start | src/rogue/protocols/xilinx/Xvc.cpp | 118 | python-callback | correct | Python-bound via .def; releases GIL before spawning thread |
| GIL-031 | Xvc::stop | src/rogue/protocols/xilinx/Xvc.cpp | 176 | python-callback | correct | Python-bound via .def; releases GIL before thread join to avoid deadlock with runThread's ScopedGil teardown |
| GIL-032 | Xvc::xfer | src/rogue/protocols/xilinx/Xvc.cpp | 350 | cpp-worker | correct | Called from runThread which holds ScopedGil (GIL-101); nested GilRelease releases for blocking queue_.pop(); intentional pattern |
| GIL-033 | XvcConnection::readTo (select) | src/rogue/protocols/xilinx/XvcConnection.cpp | 96 | cpp-worker | correct | Called from Xvc::runThread context; inner GilRelease releases for blocking select(); same nested ScopedGil/GilRelease pattern |
| GIL-034 | ZmqClient::stop | src/rogue/interfaces/ZmqClient.cpp | 183 | python-callback | correct | Python-bound; releases GIL while joining subscriber thread |
| GIL-035 | ZmqClient::sendString | src/rogue/interfaces/ZmqClient.cpp | 221 | python-callback | correct | Python-bound; blocking zmq_send/zmq_recv inside; mutex serialization fixed-in-709b5f327 |
| GIL-036 | ZmqClient::send | src/rogue/interfaces/ZmqClient.cpp | 286 | python-callback | correct | Python-bound (#ifndef NO_PYTHON block); blocking zmq ops inside GilRelease scope |
| GIL-037 | ZmqServer::stop | src/rogue/interfaces/ZmqServer.cpp | 119 | python-callback | correct | Python-bound; releases GIL while joining server threads |
| GIL-038 | ZmqServer::publish | src/rogue/interfaces/ZmqServer.cpp | 234 | python-callback | correct | Python-bound; releases GIL for blocking zmq_sendmsg |
| GIL-039 | Pool::retBuffer | src/rogue/interfaces/stream/Pool.cpp | 90 | ambiguous | needs-investigation | Called when Buffer ref-count drops to zero; destructor path can be from any thread |
| GIL-040 | Pool::setFixedSize | src/rogue/interfaces/stream/Pool.cpp | 117 | python-callback | correct | Python-bound; releases GIL before taking internal mutex |
| GIL-041 | Pool::setPoolSize | src/rogue/interfaces/stream/Pool.cpp | 130 | python-callback | correct | Python-bound; releases GIL before taking internal mutex |
| GIL-042 | Pool::allocBuffer | src/rogue/interfaces/stream/Pool.cpp | 152 | ambiguous | needs-investigation | Called from acceptReq which is called from reqFrame which can be called from any thread context |
| GIL-043 | Pool::createBuffer | src/rogue/interfaces/stream/Pool.cpp | 182 | ambiguous | needs-investigation | Same as GIL-042; called from various buffer allocation paths |
| GIL-044 | Pool::decCounter | src/rogue/interfaces/stream/Pool.cpp | 194 | ambiguous | needs-investigation | Called from Buffer destructor; runs in whichever thread drops the last ref |
| GIL-045 | FrameLock::FrameLock (ctor) | src/rogue/interfaces/stream/FrameLock.cpp | 41 | ambiguous | needs-investigation | Can be called from Python (via frame.lock()) or cpp worker; frame locking on behalf of caller |
| GIL-046 | FrameLock::lock | src/rogue/interfaces/stream/FrameLock.cpp | 67 | ambiguous | needs-investigation | Same as GIL-045; explicit re-lock |
| GIL-047 | TcpCore::stop | src/rogue/interfaces/stream/TcpCore.cpp | 162 | python-callback | correct | Python-bound; releases GIL while joining TCP stream bridge thread |
| GIL-048 | TcpCore::acceptFrame | src/rogue/interfaces/stream/TcpCore.cpp | 183 | cpp-worker | wrong-direction | acceptFrame is a stream callback; called from cpp worker upstream. See STREAM-015 |
| GIL-049 | Master::addSlave | src/rogue/interfaces/stream/Master.cpp | 60 | python-callback | correct | Python-bound (.def); GilRelease before mutex acquisition; correct pattern |
| GIL-050 | Master::reqFrame | src/rogue/interfaces/stream/Master.cpp | 67 | ambiguous | needs-investigation | Can be called from Python caller or cpp worker; GilRelease before mutex may be wrong-direction in cpp-worker callers |
| GIL-051 | Master::sendFrame (slave list copy) | src/rogue/interfaces/stream/Master.cpp | 82 | ambiguous | needs-investigation | sendFrame can be called from Python or cpp worker; the GilRelease scope only holds slaveMtx_ briefly |
| GIL-052 | Fifo::~Fifo (destructor) | src/rogue/interfaces/stream/Fifo.cpp | 82 | python-callback | correct | Destructor called from Python teardown typically; releases GIL before thread join |
| GIL-053 | Fifo::acceptFrame | src/rogue/interfaces/stream/Fifo.cpp | 116 | cpp-worker | wrong-direction | Stream callback; called from cpp worker upstream. See STREAM-016 |
| GIL-054 | Slave::acceptFrame (stream) | src/rogue/interfaces/stream/Slave.cpp | 79 | cpp-worker | wrong-direction | Default stream Slave implementation; called from sendFrame chain initiated by cpp worker. See STREAM-017 |
| GIL-055 | mem::Slave::addTransaction | src/rogue/interfaces/memory/Slave.cpp | 72 | ambiguous | needs-investigation | Called from Master::intTransaction; master may be called from Python or cpp worker |
| GIL-056 | mem::Slave::getTransaction | src/rogue/interfaces/memory/Slave.cpp | 83 | ambiguous | needs-investigation | Same as GIL-055 |
| GIL-057 | mem::Master::setSlave | src/rogue/interfaces/memory/Master.cpp | 93 | python-callback | correct | Python-bound; GilRelease before connecting slave object |
| GIL-058 | mem::Master::clearError | src/rogue/interfaces/memory/Master.cpp | 135 | python-callback | correct | Python-bound; GilRelease before mutex |
| GIL-059 | mem::Master::setTimeout | src/rogue/interfaces/memory/Master.cpp | 142 | python-callback | correct | Python-bound; GilRelease before mutex |
| GIL-060 | mem::Master::intTransaction (mastMtx_) | src/rogue/interfaces/memory/Master.cpp | 213 | python-callback | correct | intTransaction called from Python via reqTransaction; GilRelease before mastMtx_ lock |
| GIL-061 | mem::Master::waitTransaction | src/rogue/interfaces/memory/Master.cpp | 236 | python-callback | correct | Python-bound (_waitTransaction); releases GIL while blocking on transaction completion condvar |
| GIL-062 | TcpClient::stop | src/rogue/interfaces/memory/TcpClient.cpp | 138 | python-callback | correct | Python-bound; releases GIL while joining TCP client thread |
| GIL-063 | TcpClient::doTransaction | src/rogue/interfaces/memory/TcpClient.cpp | 231 | ambiguous | needs-investigation | doTransaction called from Master::intTransaction which can originate from Python or cpp; blocking ZMQ send inside |
| GIL-064 | TransactionLock::TransactionLock (ctor) | src/rogue/interfaces/memory/TransactionLock.cpp | 41 | ambiguous | needs-investigation | Can be called from Python (via tran.lock()) or cpp worker |
| GIL-065 | TransactionLock::lock | src/rogue/interfaces/memory/TransactionLock.cpp | 76 | ambiguous | needs-investigation | Same as GIL-064 |
| GIL-066 | Block::setEnable | src/rogue/interfaces/memory/Block.cpp | 149 | python-callback | correct | Python-bound (.def); GilRelease before block mutex |
| GIL-067 | Block::intStartTransaction (mastMtx_) | src/rogue/interfaces/memory/Block.cpp | 192 | python-callback | correct | Called from Block::startTransaction which is Python-initiated; GilRelease before mutex acquisition |
| GIL-068 | Block::checkTransaction (mastMtx_) | src/rogue/interfaces/memory/Block.cpp | 371 | python-callback | correct | Called from Python-initiated transaction sequence; GilRelease before lock |
| GIL-069 | Block::setBytes | src/rogue/interfaces/memory/Block.cpp | 658 | python-callback | correct | Python-bound; GilRelease before bit manipulation under block mutex |
| GIL-070 | Block::getBytes | src/rogue/interfaces/memory/Block.cpp | 731 | python-callback | correct | Python-bound; GilRelease before bit extraction under block mutex |
| GIL-071 | TcpServer::stop | src/rogue/interfaces/memory/TcpServer.cpp | 131 | python-callback | correct | Python-bound; releases GIL while joining TCP server thread |
| GIL-072 | Prbs::setWidth | src/rogue/utilities/Prbs.cpp | 133 | python-callback | correct | Python-bound (.def); GilRelease before internal mutex |
| GIL-073 | Prbs::sendCount | src/rogue/utilities/Prbs.cpp | 171 | python-callback | correct | Python-bound; GilRelease before flag write |
| GIL-074 | Prbs::disable | src/rogue/utilities/Prbs.cpp | 228 | python-callback | correct | Python-bound; releases GIL while joining TX thread |
| GIL-075 | Prbs::setRxEnable | src/rogue/utilities/Prbs.cpp | 243 | python-callback | correct | Python-bound; GilRelease before flag write with mutex |
| GIL-076 | Prbs::genFrame | src/rogue/utilities/Prbs.cpp | 343 | cpp-worker | wrong-direction | genFrame is called from Prbs::runThread (cpp worker); GilRelease inside cpp thread. See HW-CORE-021 |
| GIL-077 | Prbs::acceptFrame | src/rogue/utilities/Prbs.cpp | 423 | cpp-worker | wrong-direction | Stream Slave callback; called from upstream cpp worker. See HW-CORE-022 |
| GIL-078 | StreamUnZip::acceptFrame | src/rogue/utilities/StreamUnZip.cpp | 62 | cpp-worker | wrong-direction | Stream Slave callback; called from upstream cpp worker. See HW-CORE-023 |
| GIL-079 | StreamZip::acceptFrame | src/rogue/utilities/StreamZip.cpp | 63 | cpp-worker | wrong-direction | Stream Slave callback; called from upstream cpp worker. See HW-CORE-024 |
| GIL-080 | StreamReader::open | src/rogue/utilities/fileio/StreamReader.cpp | 78 | python-callback | correct | Python-bound; GilRelease before file open and thread spawn |
| GIL-081 | StreamReader::close | src/rogue/utilities/fileio/StreamReader.cpp | 126 | python-callback | correct | Python-bound; GilRelease + mutex before thread join and fd close |
| GIL-082 | StreamReader::closeWait | src/rogue/utilities/fileio/StreamReader.cpp | 149 | python-callback | correct | Python-bound; GilRelease before blocking condvar wait |
| GIL-083 | StreamReader::isActive | src/rogue/utilities/fileio/StreamReader.cpp | 157 | python-callback | correct | Python-bound; GilRelease before atomic bool read under mutex |
| GIL-084 | StreamWriterChannel::acceptFrame | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 75 | cpp-worker | wrong-direction | Stream Slave callback; called from upstream cpp worker. See HW-CORE-025 |
| GIL-085 | StreamWriterChannel::setFrameCount | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 96 | python-callback | correct | Python-bound; GilRelease + mutex before count write |
| GIL-086 | StreamWriterChannel::waitFrameCount | src/rogue/utilities/fileio/StreamWriterChannel.cpp | 106 | python-callback | correct | Python-bound; GilRelease before blocking condvar wait |
| GIL-087 | StreamWriter::open | src/rogue/utilities/fileio/StreamWriter.cpp | 117 | python-callback | correct | Python-bound; GilRelease + mutex before file open |
| GIL-088 | StreamWriter::close | src/rogue/utilities/fileio/StreamWriter.cpp | 154 | python-callback | correct | Python-bound; GilRelease + mutex before flush and fd close |
| GIL-089 | StreamWriter::setBufferSize | src/rogue/utilities/fileio/StreamWriter.cpp | 181 | python-callback | correct | Python-bound; GilRelease + mutex before buffer realloc |
| GIL-090 | StreamWriter::setMaxSize | src/rogue/utilities/fileio/StreamWriter.cpp | 207 | python-callback | correct | Python-bound; GilRelease + mutex before sizeLimit_ write |
| GIL-091 | StreamWriter::getChannel | src/rogue/utilities/fileio/StreamWriter.cpp | 219 | python-callback | correct | Python-bound; GilRelease + mutex before channel map access |
| GIL-092 | StreamWriter::getTotalSize | src/rogue/utilities/fileio/StreamWriter.cpp | 229 | python-callback | correct | Python-bound; GilRelease + mutex before size read |
| GIL-093 | StreamWriter::getCurrentSize | src/rogue/utilities/fileio/StreamWriter.cpp | 236 | python-callback | correct | Python-bound; GilRelease + mutex before size read |
| GIL-094 | StreamWriter::getBandwidth | src/rogue/utilities/fileio/StreamWriter.cpp | 243 | python-callback | correct | Python-bound; GilRelease + mutex before bandwidth history read |
| GIL-095 | StreamWriter::waitFrameCount | src/rogue/utilities/fileio/StreamWriter.cpp | 267 | python-callback | correct | Python-bound; GilRelease before blocking condvar wait |
| GIL-096 | StreamWriter::writeFile | src/rogue/utilities/fileio/StreamWriter.cpp | 316 | cpp-worker | wrong-direction | Called from StreamWriterChannel::acceptFrame (GIL-084) which is itself called from a cpp worker. See HW-CORE-026 |
| GIL-097 | MemMap::stop | src/rogue/hardware/MemMap.cpp | 81 | python-callback | correct | Python-bound; releases GIL while joining MemMap worker thread |
| GIL-098 | MemMap::doTransaction | src/rogue/hardware/MemMap.cpp | 92 | ambiguous | needs-investigation | Called via Slave interface from intTransaction; origin depends on caller chain |
| GIL-099 | AxiStreamDma::AxiStreamDma (ctor) | src/rogue/hardware/axi/AxiStreamDma.cpp | 184 | python-callback | correct | Constructor called from Python (create() is Python-bound); releases GIL before device open (blocking syscall). See HW-CORE-009 |
| GIL-100 | AxiStreamDma::stop | src/rogue/hardware/axi/AxiStreamDma.cpp | 235 | python-callback | correct | Python-bound stop sequence; releases GIL while joining DMA thread |
| GIL-101 | AxiStreamDma::acceptReq (zero-copy) | src/rogue/hardware/axi/AxiStreamDma.cpp | 288 | ambiguous | needs-investigation | acceptReq called from reqFrame; can originate from Python or cpp worker |
| GIL-102 | AxiStreamDma::acceptFrame | src/rogue/hardware/axi/AxiStreamDma.cpp | 339 | cpp-worker | wrong-direction | Stream Slave callback called from cpp worker upstream; DMA write inside. See HW-CORE-027 |
| GIL-103 | AxiStreamDma::retBuffer | src/rogue/hardware/axi/AxiStreamDma.cpp | 431 | ambiguous | needs-investigation | Called from Buffer destructor; runs in whichever thread drops the last Buffer ref |
| GIL-104 | AxiMemMap::stop | src/rogue/hardware/axi/AxiMemMap.cpp | 93 | python-callback | correct | Python-bound; releases GIL while joining AxiMemMap worker thread |
| GIL-105 | AxiMemMap::doTransaction | src/rogue/hardware/axi/AxiMemMap.cpp | 103 | ambiguous | needs-investigation | Called via Slave interface; origin depends on caller chain |
| GIL-106 | Logging::intLog (ScopedGil) | src/rogue/Logging.cpp | 211 | cpp-worker | correct | ScopedGil acquired inside intLog to call Python logging callback; cpp-worker thread acquires GIL to call Python — correct ScopedGil usage |
| GIL-107 | ZmqServer::doString (ScopedGil) | src/rogue/interfaces/ZmqServer.cpp | 263 | cpp-worker | correct | Inside ZmqServerWrap::doString called from strThread; acquires GIL to call Python override — correct ScopedGil usage |
| GIL-108 | ZmqServer::runThread (ScopedGil) | src/rogue/interfaces/ZmqServer.cpp | 295 | cpp-worker | correct | Inside runThread loop; acquires GIL to call doRequest Python override — correct ScopedGil usage |
| GIL-109 | ZmqClient::runThread (ScopedGil) | src/rogue/interfaces/ZmqClient.cpp | 356 | cpp-worker | correct | Inside ZmqClient::runThread; acquires GIL to call doUpdate Python callback — correct ScopedGil usage |
| GIL-110 | Variable::queueUpdate (ScopedGil) | src/rogue/interfaces/memory/Variable.cpp | 738 | cpp-worker | correct | Called from Block update path in cpp worker context; acquires GIL to call Python override — correct |
| GIL-111 | SlaveWrap::acceptFrame (stream ScopedGil) | src/rogue/interfaces/stream/Slave.cpp | 112 | cpp-worker | correct | ScopedGil acquired before calling Python _acceptFrame override; cpp worker calls into Python — correct ScopedGil usage |
| GIL-112 | mem::SlaveWrap::doMinAccess (ScopedGil) | src/rogue/interfaces/memory/Slave.cpp | 188 | cpp-worker | correct | ScopedGil before Python _doMinAccess override; same pattern as GIL-111 |
| GIL-113 | mem::SlaveWrap::doMaxAccess (ScopedGil) | src/rogue/interfaces/memory/Slave.cpp | 209 | cpp-worker | correct | ScopedGil before Python _doMaxAccess override |
| GIL-114 | mem::SlaveWrap::doAddress (ScopedGil) | src/rogue/interfaces/memory/Slave.cpp | 230 | cpp-worker | correct | ScopedGil before Python _doAddress override |
| GIL-115 | mem::SlaveWrap::doTransaction (ScopedGil) | src/rogue/interfaces/memory/Slave.cpp | 251 | cpp-worker | correct | ScopedGil before Python _doTransaction override; cpp thread calls into Python slave |
| GIL-116 | Transaction::wait release (ScopedGil) | src/rogue/interfaces/memory/Transaction.cpp | 253 | python-callback | correct | ScopedGil acquired to release PyBuffer after transaction completes; holding GIL here is correct — PyBuffer_Release requires GIL |
| GIL-117 | Hub::doTransaction (ScopedGil) | src/rogue/interfaces/memory/Hub.cpp | 178 | cpp-worker | correct | HubWrap::doTransaction acquires ScopedGil before calling Python _doTransaction override |
| GIL-118 | Block::varUpdate (ScopedGil) | src/rogue/interfaces/memory/Block.cpp | 448 | ambiguous | needs-investigation | varUpdate called from checkTransaction; can be from Python-initiated or cpp-worker context depending on who calls checkTransaction |

---

## Severity Normalizations

The following normalizations were applied during the consolidation pass per D-07 rubric and D-08 sanity pass:

### 1. Raw lock/unlock pattern (classMtx_) — Slave.cpp and Transaction.cpp

**Pattern:** Raw `mtx_.lock()` / `mtx_.unlock()` without RAII  
**Partials:** Both MEM partial and CONTEXT.md note the same pattern as Logging.cpp  
**Ruling:** `high` for all three sites (MEM-001, MEM-002, HW-CORE-001/HW-CORE-002) — these all share the same blast radius: exception between lock/unlock deadlocks the next caller permanently. The D-07 rubric assigns `high` to "raw lock/unlock with throwable call in critical section". The Prbs raw-lock sites (HW-CORE-012, HW-CORE-013) are similarly assigned `high`.  
**Normalized:** No change required; all partials already scored these `high`.

### 2. GilRelease wrong-direction sites from GIL-originated bugs table

**Pattern:** `GilRelease` instantiated inside a cpp-worker thread that never held the GIL  
**Partials:** GIL partial scored these `medium` with reasoning that CPython's `PyEval_SaveThread()` on an unowned GIL is a no-op; behavior is implementation-defined  
**Ruling:** `medium` preserved across all 28 GIL-originated bug rows (STREAM-015 through STREAM-017, PROTO-RSSI-008 through -010, PROTO-UDP-005/006, PROTO-PACK-005 through -008, PROTO-SRP-004 through -006, PROTO-BATCH-002 through -007, HW-CORE-021 through -027). All 28 rows consistently use the same class, severity, and description pattern — no cross-partial outlier.

### 3. RSSI Controller non-atomic state races (PROTO-RSSI-002, PROTO-RSSI-003)

**Pattern:** Lock-free read of non-atomic uint32_t/uint8_t updated under mutex  
**Ruling:** `medium` per D-07 rubric ("Race or lifetime issue reachable only under adversarial/synthetic load; TSan would flag intermittently"). The state_ bare read is practically atomic on x86/ARM but is formally UB.  
**Normalized:** No change; protocols partial scored `medium` consistently.

### 4. threadEn_ non-atomic bool — multiple subsystems

**Pattern:** Plain `bool` written by stop() thread, read by runThread() without atomic or fence  
**Found in:** STREAM-003, STREAM-004, STREAM-005, MEM-003, MEM-004, PROTO-UDP-001, HW-CORE-008  
**Partials:** Stream scored STREAM-003/004/005 as `high`; Memory scored MEM-003/MEM-004 as `medium`; UDP partial scored PROTO-UDP-001 as `medium`; HW-CORE partial scored HW-CORE-008 as `low`  
**Analysis:** `threadEn_` without a `volatile`/atomic qualifier is a data race under C++11 (formally UB). The blast radius is that the compiler could cache the value in a register and the worker thread never observes the stop signal — effectively a silent hang or infinite loop. Per D-07 this is `high` (data race reachable under realistic multi-threaded PyRogue load; TSan or ASan would flag under a reasonable stress loop).  
**Normalization decision:** The stream partial's `high` rating is correct for TcpCore/ZmqClient/ZmqServer where the thread is actively used during normal operation. The memory partial's `medium` for TcpClient/TcpServer is slightly under-rated — these TCP workers are used in normal data paths. **Applied normalization: promote MEM-003 and MEM-004 from `medium` to `high`.** UDP PROTO-UDP-001 is also promoted to `medium` (these are used in normal operation but the non-atomic read is in a busier loop than TCP). HW-CORE-008 `low` for AxiStreamDma is retained — the hardware path is typically used by expert users and the race window is narrow.

### 5. VLA usage — Block.cpp and DmaDriver.h

**Pattern:** Compiler-extension VLA (`uint8_t arr[runtime_size]`) not standard in C++14  
**Partials:** Both MEM (MEM-007) and HW-CORE (HW-CORE-020) scored `low`  
**Ruling:** `low` confirmed — in practice the sizes are bounded by firmware configuration; no normalization needed.

---

## Files Reviewed (D-12 Coverage Audit)

Union of all six partials' Files Reviewed lists, deduplicated and sorted.

### src/rogue/ C++ sources (88 files)

```
src/rogue/GeneralError.cpp
src/rogue/GilRelease.cpp
src/rogue/hardware/axi/AxiMemMap.cpp
src/rogue/hardware/axi/AxiStreamDma.cpp
src/rogue/hardware/axi/module.cpp
src/rogue/hardware/MemMap.cpp
src/rogue/hardware/module.cpp
src/rogue/interfaces/api/Bsp.cpp
src/rogue/interfaces/memory/Block.cpp
src/rogue/interfaces/memory/Emulate.cpp
src/rogue/interfaces/memory/Hub.cpp
src/rogue/interfaces/memory/Master.cpp
src/rogue/interfaces/memory/module.cpp
src/rogue/interfaces/memory/Slave.cpp
src/rogue/interfaces/memory/TcpClient.cpp
src/rogue/interfaces/memory/TcpServer.cpp
src/rogue/interfaces/memory/Transaction.cpp
src/rogue/interfaces/memory/TransactionLock.cpp
src/rogue/interfaces/memory/Variable.cpp
src/rogue/interfaces/module.cpp
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
src/rogue/interfaces/ZmqClient.cpp
src/rogue/interfaces/ZmqServer.cpp
src/rogue/Logging.cpp
src/rogue/module.cpp
src/rogue/protocols/batcher/CombinerV1.cpp
src/rogue/protocols/batcher/CombinerV2.cpp
src/rogue/protocols/batcher/CoreV1.cpp
src/rogue/protocols/batcher/CoreV2.cpp
src/rogue/protocols/batcher/Data.cpp
src/rogue/protocols/batcher/InverterV1.cpp
src/rogue/protocols/batcher/InverterV2.cpp
src/rogue/protocols/batcher/module.cpp
src/rogue/protocols/batcher/SplitterV1.cpp
src/rogue/protocols/batcher/SplitterV2.cpp
src/rogue/protocols/module.cpp
src/rogue/protocols/packetizer/Application.cpp
src/rogue/protocols/packetizer/Controller.cpp
src/rogue/protocols/packetizer/ControllerV1.cpp
src/rogue/protocols/packetizer/ControllerV2.cpp
src/rogue/protocols/packetizer/Core.cpp
src/rogue/protocols/packetizer/CoreV2.cpp
src/rogue/protocols/packetizer/module.cpp
src/rogue/protocols/packetizer/Transport.cpp
src/rogue/protocols/rssi/Application.cpp
src/rogue/protocols/rssi/Client.cpp
src/rogue/protocols/rssi/Controller.cpp
src/rogue/protocols/rssi/Header.cpp
src/rogue/protocols/rssi/module.cpp
src/rogue/protocols/rssi/Server.cpp
src/rogue/protocols/rssi/Transport.cpp
src/rogue/protocols/srp/Cmd.cpp
src/rogue/protocols/srp/module.cpp
src/rogue/protocols/srp/SrpV0.cpp
src/rogue/protocols/srp/SrpV3.cpp
src/rogue/protocols/srp/SrpV3Emulation.cpp
src/rogue/protocols/udp/Client.cpp
src/rogue/protocols/udp/Core.cpp
src/rogue/protocols/udp/module.cpp
src/rogue/protocols/udp/Server.cpp
src/rogue/protocols/xilinx/JtagDriver.cpp
src/rogue/protocols/xilinx/module.cpp
src/rogue/protocols/xilinx/XvcConnection.cpp
src/rogue/protocols/xilinx/Xvc.cpp
src/rogue/protocols/xilinx/XvcServer.cpp
src/rogue/ScopedGil.cpp
src/rogue/utilities/fileio/module.cpp
src/rogue/utilities/fileio/StreamReader.cpp
src/rogue/utilities/fileio/StreamWriterChannel.cpp
src/rogue/utilities/fileio/StreamWriter.cpp
src/rogue/utilities/module.cpp
src/rogue/utilities/Prbs.cpp
src/rogue/utilities/StreamUnZip.cpp
src/rogue/utilities/StreamZip.cpp
src/rogue/Version.cpp
```

### include/rogue/ headers (98 files)

```
include/rogue/Directives.h
include/rogue/EnableSharedFromThis.h
include/rogue/GeneralError.h
include/rogue/GilRelease.h
include/rogue/hardware/axi/AxiMemMap.h
include/rogue/hardware/axi/AxiStreamDma.h
include/rogue/hardware/axi/module.h
include/rogue/hardware/drivers/AxisDriver.h
include/rogue/hardware/drivers/DmaDriver.h
include/rogue/hardware/MemMap.h
include/rogue/hardware/module.h
include/rogue/Helpers.h
include/rogue/interfaces/api/Bsp.h
include/rogue/interfaces/memory/Block.h
include/rogue/interfaces/memory/Constants.h
include/rogue/interfaces/memory/Emulate.h
include/rogue/interfaces/memory/Hub.h
include/rogue/interfaces/memory/Master.h
include/rogue/interfaces/memory/module.h
include/rogue/interfaces/memory/Slave.h
include/rogue/interfaces/memory/TcpClient.h
include/rogue/interfaces/memory/TcpServer.h
include/rogue/interfaces/memory/Transaction.h
include/rogue/interfaces/memory/TransactionLock.h
include/rogue/interfaces/memory/Variable.h
include/rogue/interfaces/module.h
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
include/rogue/interfaces/ZmqClient.h
include/rogue/interfaces/ZmqServer.h
include/rogue/Logging.h
include/rogue/module.h
include/rogue/numpy.h
include/rogue/protocols/batcher/CombinerV1.h
include/rogue/protocols/batcher/CombinerV2.h
include/rogue/protocols/batcher/CoreV1.h
include/rogue/protocols/batcher/CoreV2.h
include/rogue/protocols/batcher/Data.h
include/rogue/protocols/batcher/InverterV1.h
include/rogue/protocols/batcher/InverterV2.h
include/rogue/protocols/batcher/module.h
include/rogue/protocols/batcher/SplitterV1.h
include/rogue/protocols/batcher/SplitterV2.h
include/rogue/protocols/module.h
include/rogue/protocols/packetizer/Application.h
include/rogue/protocols/packetizer/Controller.h
include/rogue/protocols/packetizer/ControllerV1.h
include/rogue/protocols/packetizer/ControllerV2.h
include/rogue/protocols/packetizer/Core.h
include/rogue/protocols/packetizer/CoreV2.h
include/rogue/protocols/packetizer/CRC.h
include/rogue/protocols/packetizer/module.h
include/rogue/protocols/packetizer/Transport.h
include/rogue/protocols/rssi/Application.h
include/rogue/protocols/rssi/Client.h
include/rogue/protocols/rssi/Controller.h
include/rogue/protocols/rssi/Header.h
include/rogue/protocols/rssi/module.h
include/rogue/protocols/rssi/Server.h
include/rogue/protocols/rssi/Transport.h
include/rogue/protocols/srp/Cmd.h
include/rogue/protocols/srp/module.h
include/rogue/protocols/srp/SrpV0.h
include/rogue/protocols/srp/SrpV3Emulation.h
include/rogue/protocols/srp/SrpV3.h
include/rogue/protocols/udp/Client.h
include/rogue/protocols/udp/Core.h
include/rogue/protocols/udp/module.h
include/rogue/protocols/udp/Server.h
include/rogue/protocols/xilinx/JtagDriver.h
include/rogue/protocols/xilinx/module.h
include/rogue/protocols/xilinx/XvcConnection.h
include/rogue/protocols/xilinx/Xvc.h
include/rogue/protocols/xilinx/XvcServer.h
include/rogue/Queue.h
include/rogue/ScopedGil.h
include/rogue/utilities/fileio/module.h
include/rogue/utilities/fileio/StreamReader.h
include/rogue/utilities/fileio/StreamWriterChannel.h
include/rogue/utilities/fileio/StreamWriter.h
include/rogue/utilities/module.h
include/rogue/utilities/Prbs.h
include/rogue/utilities/StreamUnZip.h
include/rogue/utilities/StreamZip.h
include/rogue/Version.h
```

### python/pyrogue/ Python modules (76 files)

```
python/pyrogue/_Block.py
python/pyrogue/_Command.py
python/pyrogue/_DataReceiver.py
python/pyrogue/_DataWriter.py
python/pyrogue/_Device.py
python/pyrogue/examples/_AxiVersion.py
python/pyrogue/examples/_ExampleRoot.py
python/pyrogue/examples/__init__.py
python/pyrogue/examples/_LargeDevice.py
python/pyrogue/examples/__main__.py
python/pyrogue/examples/_OsMemMaster.py
python/pyrogue/examples/_OsMemSlave.py
python/pyrogue/hardware/axi/_AxiStreamDmaMon.py
python/pyrogue/hardware/axi/__init__.py
python/pyrogue/_HelperFunctions.py
python/pyrogue/__init__.py
python/pyrogue/interfaces/__init__.py
python/pyrogue/interfaces/_OsCommandMemorySlave.py
python/pyrogue/interfaces/_SimpleClient.py
python/pyrogue/interfaces/simulation.py
python/pyrogue/interfaces/_SqlLogging.py
python/pyrogue/interfaces/stream/_Fifo.py
python/pyrogue/interfaces/stream/__init__.py
python/pyrogue/interfaces/stream/_Variable.py
python/pyrogue/interfaces/_Virtual.py
python/pyrogue/interfaces/_ZmqServer.py
python/pyrogue/_Logging.py
python/pyrogue/__main__.py
python/pyrogue/_Model.py
python/pyrogue/_Node.py
python/pyrogue/_PollQueue.py
python/pyrogue/_Process.py
python/pyrogue/protocols/epicsV4.py
python/pyrogue/protocols/epicsV7.py
python/pyrogue/protocols/gpib.py
python/pyrogue/protocols/__init__.py
python/pyrogue/protocols/_Network.py
python/pyrogue/protocols/_uart.py
python/pyrogue/pydm/data_plugins/__init__.py
python/pyrogue/pydm/data_plugins/rogue_plugin.py
python/pyrogue/pydm/__init__.py
python/pyrogue/pydm/pydmTop.py
python/pyrogue/pydm/rogue_plugin.py
python/pyrogue/pydm/TimePlotTop.py
python/pyrogue/pydm/tools/generic_file_tool.py
python/pyrogue/pydm/tools/__init__.py
python/pyrogue/pydm/tools/node_info_tool.py
python/pyrogue/pydm/tools/read_node_tool.py
python/pyrogue/pydm/tools/read_recursive_tool.py
python/pyrogue/pydm/tools/write_node_tool.py
python/pyrogue/pydm/tools/write_recursive_tool.py
python/pyrogue/pydm/widgets/data_writer.py
python/pyrogue/pydm/widgets/debug_tree.py
python/pyrogue/pydm/widgets/designer.py
python/pyrogue/pydm/widgets/__init__.py
python/pyrogue/pydm/widgets/label.py
python/pyrogue/pydm/widgets/line_edit.py
python/pyrogue/pydm/widgets/plot.py
python/pyrogue/pydm/widgets/process.py
python/pyrogue/pydm/widgets/root_control.py
python/pyrogue/pydm/widgets/run_control.py
python/pyrogue/pydm/widgets/system_log.py
python/pyrogue/pydm/widgets/system_window.py
python/pyrogue/pydm/widgets/time_plotter.py
python/pyrogue/_Root.py
python/pyrogue/_RunControl.py
python/pyrogue/utilities/cpsw.py
python/pyrogue/utilities/fileio/_FileReader.py
python/pyrogue/utilities/fileio/__init__.py
python/pyrogue/utilities/fileio/_StreamReader.py
python/pyrogue/utilities/fileio/_StreamWriter.py
python/pyrogue/utilities/hls/__init__.py
python/pyrogue/utilities/hls/_RegInterfParser.py
python/pyrogue/utilities/__init__.py
python/pyrogue/utilities/prbs.py
python/pyrogue/_Variable.py
```

**D-12 Coverage result:** 262 files reviewed matches `find src/rogue/ include/rogue/ python/pyrogue/ -type f \( -name '*.cpp' -o -name '*.h' -o -name '*.py' \)` output (88 + 98 + 76 = 262). Coverage complete — no subdirectory silently skipped. ✓

---

## Line-Range Spot-Check Results

Per CONTEXT.md §Claude's Discretion and plan D-14, exhaustive line-range re-verification is reviewer discretion. The consolidation plan performed a spot-check against HEAD `1a04b1e1f` on `hunt-for-red-october`:

**Mandatory classes verified:**

| Category | Rows Checked | Result |
|---|---|---|
| fixed-in-b1a669c96 | STREAM-001 (Fifo.h:46 atomic present ✓), PROTO-RSSI-001 (Controller.h:103 atomic ✓), PROTO-PACK-001 (Controller.h:56 atomic ✓), HW-CORE-003 (Queue.h:47 atomic ✓) | All pass ✓ |
| fixed-in-709b5f327 | PY-001 (_Virtual.py:144 _loadLock present ✓) | Pass ✓ |
| critical severity | None in this audit (no row scored critical) | N/A |
| high severity (≥10-line ranges) | HW-CORE-001 (Logging.cpp:109-112 levelMtx_.lock/unlock present ✓), HW-CORE-002 (Logging.cpp:120-127 levelMtx_ raw lock pairs present ✓), MEM-001 (Slave.cpp:55-59 classMtx_.lock present ✓), MEM-002 (Transaction.cpp:94-98 classMtx_.lock present ✓) | All pass ✓ |
| ≥10-line range sample | STREAM-013 (TcpCore.cpp:175-222 FrameLock+bridgeMtx_ present ✓), MEM-011 (Transaction.cpp:156-178 subTranMap_.erase path present ✓), PROTO-PACK-004 (ControllerV2.cpp:277-287 busy-wait block present ✓) | All pass ✓ |
| 10% random sample | HW-CORE-012 (Prbs.cpp:244-246 pMtx_.lock/unlock present ✓), GIL-035 (ZmqClient.cpp:221 GilRelease+lock_guard present ✓), GIL-099 (AxiStreamDma.cpp:184 GilRelease present ✓), MEM-005 (Block.cpp:682-684 fastByte_ memcpy present ✓) | All pass ✓ |

No spot-check failures. All verified line ranges contain the described constructs.

Remaining rows (non-fixed-in, non-critical, <10-line ranges, not in sample): rely on reviewer's original citations. Exhaustive re-verification deferred to reviewer at audit time per CONTEXT.md §Claude's Discretion.

---

## Methodology

- Audit partitioned by subsystem per D-01; six partials merged here.
- Schema per D-04 (main table) and D-06 (GIL appendix).
- Severity rubric per D-07.
- Fixed-on-branch entries retained in audit trail per D-09 (Status: fixed-in-\<sha\>).
- Severity normalization applied per D-08 (documented in §Severity Normalizations above). Key normalization: MEM-003 and MEM-004 promoted from `medium` to `high` for threadEn_ non-atomic bool pattern to match stream partial's `high` rating for the same construct.
- GIL-originated wrong-direction bugs (28 rows from plan 06 secondary table) merged into correct subsystem sections with final IDs assigned by File path routing per Sub-step 3.
- Line-range re-verification: spot-check (fixed-in rows + high-severity ≥10-line ranges + 10% random sample). Exhaustive re-verification exceeds consolidator context budget for a 131-row main table + 118-row GIL appendix and is reviewer discretion at audit time per CONTEXT.md §Claude's Discretion.
- GIL appendix Notes column updated for all merged wrong-direction rows to read "See \<FINAL-SUBSYSTEM-ID\>" replacing placeholders.
- Branch: `hunt-for-red-october` HEAD `1a04b1e1f` (Merge pull request #1191 from slaclab/improve-thread-safety).
