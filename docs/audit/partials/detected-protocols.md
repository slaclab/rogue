# Protocols Subsystem — Audit Partial

**Reviewer:** Plan 01-03 execution agent
**Branch:** hunt-for-red-october (HEAD 1a04b1e1f)
**Date:** 2026-04-23

---

## Files Reviewed

### src/rogue/protocols/

- src/rogue/protocols/module.cpp
- src/rogue/protocols/batcher/CombinerV1.cpp
- src/rogue/protocols/batcher/CombinerV2.cpp
- src/rogue/protocols/batcher/CoreV1.cpp
- src/rogue/protocols/batcher/CoreV2.cpp
- src/rogue/protocols/batcher/Data.cpp
- src/rogue/protocols/batcher/InverterV1.cpp
- src/rogue/protocols/batcher/InverterV2.cpp
- src/rogue/protocols/batcher/module.cpp
- src/rogue/protocols/batcher/SplitterV1.cpp
- src/rogue/protocols/batcher/SplitterV2.cpp
- src/rogue/protocols/packetizer/Application.cpp
- src/rogue/protocols/packetizer/Controller.cpp
- src/rogue/protocols/packetizer/ControllerV1.cpp
- src/rogue/protocols/packetizer/ControllerV2.cpp
- src/rogue/protocols/packetizer/Core.cpp
- src/rogue/protocols/packetizer/CoreV2.cpp
- src/rogue/protocols/packetizer/module.cpp
- src/rogue/protocols/packetizer/Transport.cpp
- src/rogue/protocols/rssi/Application.cpp
- src/rogue/protocols/rssi/Client.cpp
- src/rogue/protocols/rssi/Controller.cpp
- src/rogue/protocols/rssi/Header.cpp
- src/rogue/protocols/rssi/module.cpp
- src/rogue/protocols/rssi/Server.cpp
- src/rogue/protocols/rssi/Transport.cpp
- src/rogue/protocols/srp/Cmd.cpp
- src/rogue/protocols/srp/module.cpp
- src/rogue/protocols/srp/SrpV0.cpp
- src/rogue/protocols/srp/SrpV3.cpp
- src/rogue/protocols/srp/SrpV3Emulation.cpp
- src/rogue/protocols/udp/Client.cpp
- src/rogue/protocols/udp/Core.cpp
- src/rogue/protocols/udp/module.cpp
- src/rogue/protocols/udp/Server.cpp
- src/rogue/protocols/xilinx/JtagDriver.cpp
- src/rogue/protocols/xilinx/module.cpp
- src/rogue/protocols/xilinx/XvcConnection.cpp
- src/rogue/protocols/xilinx/Xvc.cpp
- src/rogue/protocols/xilinx/XvcServer.cpp

### include/rogue/protocols/

- include/rogue/protocols/module.h
- include/rogue/protocols/batcher/CombinerV1.h
- include/rogue/protocols/batcher/CombinerV2.h
- include/rogue/protocols/batcher/CoreV1.h
- include/rogue/protocols/batcher/CoreV2.h
- include/rogue/protocols/batcher/Data.h
- include/rogue/protocols/batcher/InverterV1.h
- include/rogue/protocols/batcher/InverterV2.h
- include/rogue/protocols/batcher/module.h
- include/rogue/protocols/batcher/SplitterV1.h
- include/rogue/protocols/batcher/SplitterV2.h
- include/rogue/protocols/packetizer/Application.h
- include/rogue/protocols/packetizer/Controller.h
- include/rogue/protocols/packetizer/ControllerV1.h
- include/rogue/protocols/packetizer/ControllerV2.h
- include/rogue/protocols/packetizer/Core.h
- include/rogue/protocols/packetizer/CoreV2.h
- include/rogue/protocols/packetizer/CRC.h
- include/rogue/protocols/packetizer/module.h
- include/rogue/protocols/packetizer/Transport.h
- include/rogue/protocols/rssi/Application.h
- include/rogue/protocols/rssi/Client.h
- include/rogue/protocols/rssi/Controller.h
- include/rogue/protocols/rssi/Header.h
- include/rogue/protocols/rssi/module.h
- include/rogue/protocols/rssi/Server.h
- include/rogue/protocols/rssi/Transport.h
- include/rogue/protocols/srp/Cmd.h
- include/rogue/protocols/srp/module.h
- include/rogue/protocols/srp/SrpV0.h
- include/rogue/protocols/srp/SrpV3Emulation.h
- include/rogue/protocols/srp/SrpV3.h
- include/rogue/protocols/udp/Client.h
- include/rogue/protocols/udp/Core.h
- include/rogue/protocols/udp/module.h
- include/rogue/protocols/udp/Server.h
- include/rogue/protocols/xilinx/JtagDriver.h
- include/rogue/protocols/xilinx/module.h
- include/rogue/protocols/xilinx/XvcConnection.h
- include/rogue/protocols/xilinx/Xvc.h
- include/rogue/protocols/xilinx/XvcServer.h

---

## Findings Table

| ID | File | Lines | Class | Severity | Description | Status | Repro Hypothesis | Reference |
|----|------|-------|-------|----------|-------------|--------|-----------------|-----------|
| PROTO-RSSI-001 | src/rogue/protocols/rssi/Controller.cpp | 64-77 | threading | high | Controller fields dropCount_, remBusy_, locBusy_, downCount_, retranCount_, locBusyCnt_, remBusyCnt_, threadEn_ were non-atomic uint32_t/bool read from network-IO thread and written from controller worker thread, creating data races under concurrent RSSI operation. | fixed-in-b1a669c96 | TSan race under N-parallel RSSI frame push while runThread reads any of these fields | CONCERNS.md §Thread-Safety-Concerns |
| PROTO-RSSI-002 | src/rogue/protocols/rssi/Controller.cpp | 125-131, 202-219 | threading | medium | Fields state_, locConnId_, remConnId_, locTryPeriod_ are read in transportRx() (network-IO thread) at lines 202-219 (state_ read bare without stMtx_) while the state machine in runThread() writes them under stMtx_; reads in transportRx are lock-free. Investigation verdict: state_ is written only by runThread under stMtx_ but read lock-free in transportRx (line 202: `if (state_ == StOpen || state_ == StWaitSyn)`). locConnId_ and remConnId_ are written only in the constructor and in stateClosedWait (runThread) — safe because constructor completes before threads start, and stateClosedWait writes happen under the runThread context without lock. locTryPeriod_ is written by setLocTryPeriod() without synchronization (any thread) and read by runThread. Conclusion: state_ bare read is a narrow-window benign race (uint32_t read is practically atomic on x86/ARM but formally UB); locTryPeriod_ set/read is an unsynchronized write-read race. | detected | TSan would flag the bare state_ read in transportRx vs write in runThread; locTryPeriod_ set vs runThread read | CONCERNS.md §Thread-Safety-Concerns; STATE.md §Blockers |
| PROTO-RSSI-003 | src/rogue/protocols/rssi/Controller.cpp | 391-412 | threading | medium | applicationRx() busy-waits on txListCount_ >= curMaxBuffers_ (lines 398-406) with bare usleep(10) loop; txListCount_ is a plain uint8_t written under txMtx_ by transportTx/transportRx, but read in applicationRx without holding txMtx_ — a lock-free read of a non-atomic field updated under mutex. | detected | TSan race between transportRx ACK processing (txMtx_ held) and applicationRx txListCount_ read | CONCERNS.md §Thread-Safety-Concerns |
| PROTO-RSSI-004 | src/rogue/protocols/rssi/Controller.cpp | 415-418 | threading | low | getOpen() reads state_ lock-free from Python thread context; state_ is uint32_t written by runThread without mutex on the result path (stateError, stateSendSynAck etc). This is a public status API — the race is practically harmless on x86/ARM but is formally UB and TSan-visible. | detected | TSan race between getOpen() call and runThread state transitions | CONCERNS.md §Thread-Safety-Concerns |
| PROTO-RSSI-005 | src/rogue/protocols/rssi/Controller.cpp | 580-588, 64-77 | logic | low | resetCounters() resets atomic fields without coordination with runThread or transportRx — the counters may increment immediately after reset from a concurrent thread, producing a misleading near-zero reading. This is a monitoring/observability concern, not a correctness bug. | detected | None — statistical; any concurrent RSSI activity will re-increment within ms of reset | CONCERNS.md §Tech-Debt |
| PROTO-RSSI-006 | src/rogue/protocols/rssi/Controller.cpp | 86-88 | logic | low | Default RSSI timeout parameters (locRetranTout_=20ms, locCumAckTout_=5ms) are hard-coded at construction; these values are tuned for deterministic FPGA UDP stacks and cause spurious retransmits on macOS and loaded CI hosts. Not a race but a fragile constant. | detected | Observed: macOS RSSI loopback tests skip to avoid this; CI integration tests use relaxed timeout override | CONCERNS.md §Tech-Debt §RSSI-Retransmission-Timeout-Sensitivity |
| PROTO-RSSI-007 | src/rogue/protocols/rssi/Application.cpp | 91-99 | threading | medium | Application::runThread() tight-loops calling cntl_->applicationTx() without any GilRelease; applicationTx() internally acquires GilRelease (line 341 of Controller.cpp) but the tight loop in runThread does not yield Python between calls. The thread is a std::thread worker — adding GilRelease here would be wrong-direction; the loop itself simply burns CPU when idle since Queue::pop() blocks correctly inside applicationTx. No threading safety issue — the loop is correct, just potentially high-CPU. Logged as logic/low for audit completeness. | detected | High CPU idle on RSSI Application thread | — |
| PROTO-UDP-001 | src/rogue/protocols/udp/Client.cpp, src/rogue/protocols/udp/Server.cpp | 113-126, 107-119 | threading | medium | UDP Client and Server stop() check threadEn_ then join thread, but threadEn_ is a plain bool (include/rogue/protocols/udp/Client.h, Server.h). The flag is written by the main thread and read by runThread without synchronization. At current HEAD the fields appear as non-atomic members — a data race that TSan would flag on platforms where the compiler reloads from memory in the worker loop. | detected | TSan race between stop() writing threadEn_=false and runThread reading threadEn_ in while loop | — |
| PROTO-UDP-002 | src/rogue/protocols/udp/Client.cpp | 192-243 | threading | low | Client::runThread() calls recvfrom without timeout (blocking indefinitely when no data arrives). On stop(), threadEn_ is cleared but the blocking recvfrom may not unblock promptly — thread join in stop() will block until the next UDP packet arrives or the OS times out the socket. This is a shutdown-latency issue, not a corruption race. | detected | stop() may hang if no UDP traffic; observed in integration tests as slow teardown | — |
| PROTO-UDP-003 | src/rogue/protocols/udp/Server.cpp | 232-244 | threading | low | Server::runThread() updates remAddr_ (shared with acceptFrame's sendmsg path) under udpMtx_, but the memcmp comparison at line 233 reads remAddr_ without the mutex before deciding whether to lock. This is a benign check-then-lock pattern (the update happens under lock), but TSan may flag the unlocked remAddr_ read preceding the lock acquisition. | detected | TSan race between runThread memcmp(remAddr_) and acceptFrame reading remAddr_ under udpMtx_ | — |
| PROTO-UDP-004 | src/rogue/protocols/udp/Client.cpp | 183-187 | logic | low | Client::acceptFrame() select-then-sendmsg loop does not check errno after sendmsg returns < 0; the EAGAIN/EINTR loop condition is `res == 0`, so a hard socket error (errno != EAGAIN) falls through to the next buffer iteration without logging the specific failure reason. | detected | Difficult to trigger; normally a network error would appear in log warning but the retry continues | — |
| PROTO-PACK-001 | include/rogue/protocols/packetizer/Controller.h | 56 | threading | medium | Controller::dropCount_ was a non-atomic uint32_t incremented in transportRx (transport thread) and read by getDropCount() from arbitrary threads (Python polling, diagnostics), creating a lock-free read-of-non-atomic race. Converted to std::atomic<uint32_t> in commit b1a669c96, matching the RSSI Controller atomics pattern identified in CONCERNS.md §Thread-Safety-Concerns (RSSI Monitor note "audit ControllerV2 (packetizer) for similar pattern"). | fixed-in-b1a669c96 | TSan race under concurrent packetizer transportRx + Python getDropCount() poll | CONCERNS.md §Thread-Safety-Concerns |
| PROTO-PACK-002 | src/rogue/protocols/packetizer/ControllerV2.cpp | 242 | logic | low | ControllerV2::transportRx() at line 242 calls `tranFrame_[tmpDest]->setError(0x80)` after `tranFrame_[tmpDest].reset()` on the EOF path (line 239). After reset(), tranFrame_[tmpDest] is a null shared_ptr; the setError call will dereference null and crash. This is a use-after-free/null-deref bug. | detected | Any RSSI+packetizer session with an SSI EOF error on the last packet of a transfer will crash the process | — |
| PROTO-PACK-003 | src/rogue/protocols/packetizer/ControllerV1.cpp | 174 | logic | low | ControllerV1::transportRx() at line 174 same pattern: `tranFrame_[tmpDest]->setError(0x80)` after `tranFrame_[0].reset()`. Uses tranFrame_[tmpDest] but the reset was on tranFrame_[0] — double bug: (a) index mismatch (tmpDest vs 0), and (b) even if the index were correct, the shared_ptr was already reset. Will crash if enSsi_ is set and an SSI error arrives at EOF. | detected | Any ControllerV1 SSI-enabled session receiving an error on last packet of a transfer | — |
| PROTO-PACK-004 | src/rogue/protocols/packetizer/ControllerV2.cpp | 277-287 | threading | low | ControllerV2::applicationRx() busy-waits on tranQueue_.busy() with usleep(10) while holding appMtx_; tranQueue_ uses its own internal mutex. A concurrent transportRx could be blocked trying to acquire appMtx_ (which it does not — actually transportRx holds tranMtx_, not appMtx_). The concern is that applicationRx holds appMtx_ during the entire busy-wait, preventing any other concurrent applicationRx call. This is by design (serializes app→transport enqueue), but the critical section is extended unnecessarily long by the polling. | detected | Under high application load the appMtx_ busy-wait extends indefinitely; no deadlock but CPU waste | — |
| PROTO-SRP-001 | src/rogue/protocols/srp/SrpV3Emulation.cpp | 96-115 | threading | low | SrpV3Emulation::runThread() reads threadEn_ under queMtx_ at condition wait (line 103) but the initial check at line 100 (`while (threadEn_)`) reads it lock-free. This is a benign double-checked pattern (the wait uses a lambda that re-checks under lock), but the outer while read is lock-free. On the stop() path, threadEn_ is set to false under queMtx_ (line 86), then notify_all() fires — the lock-free outer read will eventually see false. Formally a benign race but TSan may flag it. | detected | TSan race between stop() writing threadEn_ under queMtx_ and runThread reading threadEn_ in outer while | — |
| PROTO-SRP-002 | src/rogue/protocols/srp/SrpV3Emulation.cpp | 271-317 | threading | low | processFrame() holds memMtx_ for the entire write + response-build + sendFrame sequence (line 271-316). sendFrame() may block waiting for frame allocation from the downstream transport — holding memMtx_ during a potentially blocking call prevents concurrent reads or writes from being processed. Not a race but a lock-contention/liveness issue under load. | detected | Any slow downstream transport will serialize all SRP emulation I/O behind memMtx_ during sendFrame | — |
| PROTO-SRP-003 | src/rogue/protocols/srp/SrpV0.cpp | 237-246 | logic | low | SrpV0::acceptFrame() returns without calling tran->done() on two error paths (line 239: bad frame length; line 243: header mismatch), leaving the Transaction stuck in the active table until timeout. This matches a known pattern in memory Slave implementations — a transaction that never completes blocks the calling thread at the timeout duration. | detected | SRP hardware returning a malformed response; transaction hangs for timeout duration | — |
| PROTO-XVC-001 | src/rogue/protocols/xilinx/XvcConnection.cpp, src/rogue/protocols/xilinx/XvcServer.cpp | 57, 202 (XvcConnection.cpp) | logic | low | XVC TCP socket operates without TLS or any authentication layer; raw JTAG operations (read firmware, write registers, full debug control of FPGA) are exposed in plaintext on the configured port. Any host with network access to the XVC port can execute arbitrary JTAG operations. Documented as a deployment-layer concern (XVC is typically on isolated lab networks), deferred to V2-04. | detected | Network-accessible XVC port on shared or non-isolated infrastructure | CONCERNS.md §Security-Considerations |
| PROTO-XVC-002 | src/rogue/protocols/xilinx/Xvc.cpp | 169-221 | threading | medium | Xvc::stop() uses a self-pipe (wakeFd_[1]) and queue_.stop() to unblock XvcServer::run and XvcConnection::readTo, which both release the GIL across blocking select(). The shutdown sequence is correct — threadEn_ exchange, wakeFd_ write, thread join — but the intermediate state between queue_.stop() (line 194) and wakeFd_ write (line 205) leaves any active XvcConnection::readTo select() blocked if wakeFd_ write is delayed by EINTR. The retry loop handles EINTR on the write side, but select() in readTo may miss the first byte and block a second iteration's worth of I/O before wakeFd becomes readable. In practice negligible (single EINTR round-trip is microseconds). | detected | Concurrent XVC client connected + stop() called while EINTR loop runs | CONCERNS.md §Test-Coverage-Gaps XVC-Thread-Shutdown |
| PROTO-XVC-003 | src/rogue/protocols/xilinx/Xvc.cpp | 289-296 | logic | low | Xvc::acceptFrame() silently discards incoming frames when tranQueue_.busy() returns true (line 291: `if (!queue_.busy()) queue_.push(frame)`). If downstream is congested, reply frames are dropped without logging or notifying the caller. The XVC protocol is synchronous so each xfer() call expects exactly one reply — a dropped reply causes xfer() to block in queue_.pop() until the next (mis-matched) reply arrives or stop() is called. | detected | Downstream congestion while XVC client is active; xfer() hangs indefinitely | — |
| PROTO-BATCH-001 | src/rogue/protocols/batcher/CombinerV1.cpp, src/rogue/protocols/batcher/CombinerV2.cpp | 107-113, 93-99 | threading | low | CombinerV1::acceptFrame() and CombinerV2::acceptFrame() acquire mtx_ after calling frame->lock() (GilRelease then FrameLock then mutex). The lock ordering is: GilRelease → FrameLock → mtx_. sendBatch() acquires mtx_ first (no FrameLock at mtx_ acquisition time) then acquires FrameLock per-frame inside the loop (line 165 CombinerV1, line 141 CombinerV2). These orderings are consistent and do not invert — acceptFrame holds FrameLock then mtx_; sendBatch holds mtx_ then acquires individual FrameLocks. No deadlock risk since FrameLock is per-frame. | detected-only | No plausible deadlock path found; logged for audit completeness | — |

---

## Notes

### RSSI Multi-Field State Coherence Investigation (STATE.md §Blockers/Concerns)

**Verdict: partially coherent; locTryPeriod_ is an unguarded race; state_ reads in transportRx are formally UB.**

Fields examined: `state_`, `locConnId_`, `remConnId_`, `locTryPeriod_`

- **state_** (uint32_t, line 125 Controller.h): Written exclusively by `runThread()` via state-machine functions. Read lock-free in `transportRx()` at lines 202, 239, 245, 253 (e.g., `if (state_ == StOpen || state_ == StWaitSyn)`). Also read lock-free in `getOpen()`, `applicationRx()` (line 393). No `stMtx_` held at these read sites. This is a formal data race (C++11 memory model: concurrent non-atomic write + read = UB). On x86/ARM the 32-bit load is atomic in practice, but TSan will flag it. Logged as PROTO-RSSI-002 (medium).

- **locConnId_** (uint32_t, line 131): Set once in the constructor (`locConnId_ = 0x12345678`, line 99 Controller.cpp) before any thread starts. Also set in `setLocTryPeriod()` — wait, actually locConnId_ is only set in constructor. Read in `stateClosedWait()` (runThread context, line 835). No concurrent access after construction. **Coherent.** No finding needed.

- **remConnId_** (uint32_t, line 131): Set to 0 in constructor. Written in `stateClosedWait()` (runThread context, but inspection of Controller.cpp shows remConnId_ is never actually written after construction at HEAD — the field is declared but only initialized). **Coherent.** No finding.

- **locTryPeriod_** (uint32_t, line 70): Set in constructor and in `setLocTryPeriod()` which is a public API callable from any thread (Python). Read by `runThread()` inside `stateClosedWait()` at line 819 (implicit via tryPeriodD1_/tryPeriodD4_ which are updated by setLocTryPeriod). Actually the time structs are recomputed in setLocTryPeriod(), which is the race — concurrent setLocTryPeriod() and runThread reading tryPeriodD1_/tryPeriodD4_. These are struct timeval fields (two long ints), not atomic — a torn read is possible. Logged as PROTO-RSSI-002.

**Phase 4 implication:** state_ race should be fixed with either `std::atomic<uint32_t>` (simple if only single-bit comparisons needed) or extending stMtx_ to cover transportRx reads. The existing b1a669c96 atomics pattern is the preferred approach.

### GilRelease Usage in Protocol Workers

- `Controller::runThread()` (rssi): does NOT use GilRelease; it is a `std::thread` worker — correct, no GIL held. Functions called from runThread (`stateOpen`, `stateError`, etc.) also correct. Cross-ref plan 06 (GIL audit): runThread correctly has no GilRelease.
- `Application::runThread()` (rssi): std::thread worker, no GilRelease — correct.
- `transportRx()`, `applicationTx()`, `applicationRx()`: all start with `rogue::GilRelease noGil` — correct, these may be called from Python-originated threads.
- UDP `Client::runThread()`, `Server::runThread()`: std::thread workers, no GilRelease — correct.
- `Xvc::runThread()`: uses `rogue::ScopedGil` at entry to attach a Python tstate for Master::sendFrame callbacks into Python ris.Slave subclasses. GilRelease is used inside blocking sections (XvcServer::run, XvcConnection::readTo). This is correct and well-documented in comments.

### ZmqServer Concurrent Update (CONCERNS.md §Test-Coverage-Gaps)

Per CONCERNS.md, test added in commit b1a669c96 exercises the ZmqServer concurrent update race. ZmqServer.cpp is outside the protocols/ partition — not reviewed here but noted as covered by the committed test.

---

## Sub-namespace Summary

| Sub-namespace | Files | Findings | Notes |
|---------------|-------|----------|-------|
| RSSI | 7 src + 7 include | 7 | Atomics fixed in b1a669c96; state_ bare reads remain; locTryPeriod_ race new finding |
| UDP | 3 src + 3 include | 4 | threadEn_ non-atomic; shutdown latency; remAddr_ benign race |
| TCP | 0 | 0 | No TCP sub-namespace under protocols/ |
| Packetizer | 7 src + 8 include | 4 | dropCount_ fixed; two null-deref bugs in SSI error paths; appMtx_ busy-wait |
| SRP | 4 src + 4 include | 3 | SrpV0 missing tran->done(); SrpV3Emulation lock-free threadEn_ read; memMtx_ during sendFrame |
| XVC | 4 src + 4 include | 3 | Raw socket security; stop() shutdown race window; acceptFrame silent drop |
| Batcher | 10 src + 10 include | 1 | Lock ordering consistent; no deadlock risk |
