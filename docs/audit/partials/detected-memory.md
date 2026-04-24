# Memory Subsystem Partial Findings

**Reviewer:** Phase 01 plan 02  
**Audit date:** 2026-04-23  
**Branch:** `hunt-for-red-october` at `1a04b1e1f`

---

## Files Reviewed

```
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
```

---

## Findings

| ID | File | Lines | Class | Severity | Description | Status | Repro Hypothesis | Reference |
|----|------|-------|-------|----------|-------------|--------|------------------|-----------|
| MEM-001 | src/rogue/interfaces/memory/Slave.cpp | 55-59 | threading | high | `classMtx_.lock()` / `.unlock()` used raw without RAII; if `classIdx_` increment or store throws (unlikely on x86, but UB-possible), the lock leaks and every subsequent Slave construction deadlocks. | detected | Inject exception between lines 55-59 under TSAN stress; static analysis via `-fsanitize=thread` should flag the non-RAII pattern at init time. | CONCERNS.md §Logging Mutex Manual Lock Pattern (analogous) |
| MEM-002 | src/rogue/interfaces/memory/Transaction.cpp | 94-98 | threading | high | `classMtx_.lock()` / `.unlock()` used raw without RAII in `Transaction::Transaction()`; same deadlock-on-exception risk as MEM-001. `rogue::Logging::create()` at line 92, which can allocate and throw, executes before the classMtx_ section—but any future reorder inside the ctor (or exception from `classIdx_++` on architectures without hardware atomicity) leaves the lock held. | detected | Run TSAN + construction stress under OOM pressure; static analysis flags the bare lock/unlock pair. | CONCERNS.md §Logging Mutex Manual Lock Pattern |
| MEM-003 | src/rogue/interfaces/memory/TcpClient.cpp | 117-139 | threading | medium | `threadEn_` is a plain `bool` written by `stop()` (from Python/main thread) and read by `runThread()` (from `std::thread` worker) without any lock or `std::atomic` qualification; the worker loop reads `threadEn_` in `while (threadEn_)` and `do { } while (threadEn_ && more)`, producing a data race on a non-atomic variable. | detected | TSan will flag this; run the TcpClient integration test under TSan. | — |
| MEM-004 | src/rogue/interfaces/memory/TcpServer.cpp | 101-159 | threading | medium | Same non-atomic `threadEn_` pattern as MEM-003 in TcpServer; `stop()` writes `threadEn_ = false` from the calling thread while `runThread()` reads it in `while (threadEn_)` and `do { } while (threadEn_ && more)`. | detected | TSan will flag this under stop/join concurrent with recv loop. | — |
| MEM-005 | src/rogue/interfaces/memory/Block.cpp | 660-724 | memory | medium | `setBytes` for list variables with `fastByte_` uses `memcpy(blockData_ + var->fastByte_[index], buff, var->valueBytes_)` (line 684); `var->fastByte_[index]` is an offset computed assuming `valueBits_` is byte-aligned, but `var->valueBytes_` is `ceil(valueBits_/8)` while the stride gap between `fastByte_` slots is `valueStride_/8` bytes. If `valueBytes_ > valueStride_/8` (which can happen when `valueBits_` equals `valueStride_` and both are not multiples of 8), the memcpy overruns into the next slot's region of `blockData_`. The condition guarding `fastByte_` usage in `Variable.cpp` (line 216: `valueBits_%8==0 && valueStride_%8==0`) partially mitigates this but does not check that `valueBytes_ <= stride_bytes`. | detected | Construct a list variable with `valueBits_=8, valueStride_=8, numValues_=N` and a block of exactly `N` bytes; write to last index and check adjacent bytes. | CONCERNS.md §Excessive memcpy in Memory Transaction Path |
| MEM-006 | src/rogue/interfaces/memory/Block.cpp | 660-760 | memory | low | `setBytes` calls `malloc(var->valueBytes_)` for byte-reversed copies (line 666) and stores the result in `buff`; there is no null-check on the malloc return. On malloc failure, `buff` is NULL, `memcpy(buff, data, ...)` at line 667 dereferences NULL causing a crash. This is reachable from Python API. | detected | Pass a byteReverse variable under extreme memory pressure; ASan will catch the NULL deref. | — |
| MEM-007 | src/rogue/interfaces/memory/Block.cpp | 463 | logic | low | `addVariables` uses a variable-length array (VLA) `uint8_t excMask[size_]` (line 463) which is a GCC extension and not standard C++14; in C++14 VLAs are not part of the standard and their behavior on stack-overflow (large `size_`) is implementation-defined. If a Block is constructed with a large `size_` value, this silently overflows the stack. Same pattern on line 464 (`oleMask`). | detected | Create a Block with `size_` near the stack limit; ASAN stack overflow detection would fire. | — |
| MEM-008 | src/rogue/interfaces/memory/Block.cpp | 1739-1903 | logic | low | Float-format coercion functions (`floatToHalf`, `halfToFloat`, `floatToFloat8`, etc.) handle NaN and infinity explicitly and correctly (NaN preserved or clamped, infinity clamped to max-finite where the format has no infinity). No subnormal data-corruption bug found. `floatToHalf` subnormal path (lines 1745-1750) shifts by `14-exponent` which is correct for E5M10. No NaN-to-wrong-int conversion bug: the float↔int paths (`setFloat`/`getFloat`) use direct `memcpy` of the IEEE bit pattern, avoiding any `static_cast<int>(NaN)` undefined behavior. **Finding: no bug — region covered, design correct.** | detected | (No repro required — no bug found.) | CONCERNS.md §Block Float Coercion Edge Cases |
| MEM-009 | src/rogue/interfaces/memory/Block.cpp | 1711-1732 | logic | low | `setFloat` range check (line 1714) uses `val > var->maxValue_ || val < var->minValue_` with `float` comparisons against `double` min/maxValue_; if `val` is NaN, both comparisons are `false` so NaN silently passes range validation and is stored into the block data. A NaN register write sends undefined bit patterns to FPGA registers. Same issue applies to `setDouble`, `setFloat16`, `setFloat8`, `setBFloat16`, `setFloat6`, `setFloat4`. | detected | Pass `float('nan')` from Python to a float-typed variable with min/max set; verify it stores silently. | CONCERNS.md §Block Float Coercion Edge Cases |
| MEM-010 | src/rogue/interfaces/memory/Block.cpp | 287-318 | logic | low | `startTransaction` (C++ variant, line 287) catches `rogue::GeneralError err` by value, not by `const reference`; copying an exception object is legal but `checkTransaction` may also throw from `waitTransaction` which is not caught here — it propagates out. Additionally the same pattern exists in `startTransactionPy`. The `fWr = true` assignment after a throw indicates the stale state is assumed lost, but if the exception leaves `mtx_` locked (it does not, since `waitTransaction` acquires and releases internally), the Block would deadlock. Not a bug as currently written, but fragile: any future refactor that moves `waitTransaction` outside the inner lock_guard would create a deadlock window. | detected | Code review — fragile contract not immediately exploitable. | — |
| MEM-011 | src/rogue/interfaces/memory/Transaction.cpp | 156-178 | threading | medium | `Transaction::done()` calls `parentTran->subTranMap_.erase(id_)` (line 173) and `parentTran->done()` (line 176) while holding the _child_ transaction's `lock_` but NOT the _parent's_ `lock_`. If two sibling sub-transactions complete concurrently from two hardware-response threads, both call `parentTran->subTranMap_.erase()` simultaneously, producing a data race on `subTranMap_`. Likewise `parentTran->done()` at line 176 and `parentTran->error()` at line 206 both call `cond_.notify_all()` on the parent without holding the parent's `lock_`, which is a race with `parentTran->wait()` that holds `lock_` under `unique_lock`. | detected | Create a transaction with two sub-transactions and complete them from two parallel threads simultaneously; TSan will flag the concurrent `subTranMap_.erase()`. | — |
| MEM-012 | src/rogue/interfaces/memory/Emulate.cpp | 93 | logic | low | `Emulate::doTransaction` logs every allocation at `debug` level (line 93: `log_->debug("Allocating block...")`). CONCERNS.md records this as `INFO` level but the current code uses `debug`. Either way, high-frequency allocation in test loops generates noise. No security or correctness issue; code smell / logging hygiene. | detected | Run emulator with many allocations and check log output. | CONCERNS.md §Memory Emulator Allocation Logging Noise |
| MEM-013 | src/rogue/interfaces/memory/Master.cpp | 419-428 | logic | low | `anyBits` aligned branch (lines 423-426) checks only `dstData[dstByte] != 0` (one byte at a time) but decrements `rem` by 8 bits and advances `dstByte` by 1, which is correct for `bytes == 1`; however `bytes = rem / 8` may be > 1 (when `rem >= 16` bits remain aligned) and the loop body only checks one byte, not all `bytes` bytes. The aligned branch should loop over `bytes` bytes (like `setBits` does with `memset`) but instead checks a single byte and exits early on `true`. This means `anyBits` returns `true` correctly when the first aligned byte is nonzero but skips subsequent aligned bytes if the first is zero—the result can be a false `false` return. Impact: verify-mask checks may silently pass when subsequent bytes contain set bits. | detected | Construct a bit mask with zero first byte and nonzero second byte in the aligned region; call `anyBits` over that span and confirm it returns `false` incorrectly. | — |
| MEM-014 | src/rogue/interfaces/memory/Block.cpp | 192-283 | threading | low | `intStartTransaction` holds `mtx_` lock while calling `waitTransaction(0)` (line 194) and `reqTransaction(...)` (line 282). `waitTransaction` in Master.cpp acquires `mastMtx_` internally; `reqTransaction` also acquires `mastMtx_`. The lock ordering is `mtx_` → `mastMtx_`. If any other code path acquires `mastMtx_` first and then attempts to acquire `mtx_`, a deadlock would occur. Current code does not invert this order, but the implicit lock-order dependency is undocumented and fragile. | detected | Static lock-order analysis; no immediate deadlock found under current call graph. | — |
| MEM-015 | src/rogue/interfaces/memory/TransactionLock.cpp | 40-53 | threading | low | `TransactionLock::TransactionLock()` traverses the `parentTransaction_` chain (lines 45-51) while holding `GilRelease` but without any lock on either the child or parent transactions. If a concurrent thread modifies `tran_->isSubTransaction_` or `tran_->parentTransaction_` during this traversal, the walk may dereference a dangling parent or use stale `isSubTransaction_` state. In practice the sub-transaction chain is set once at creation and not modified concurrently, making this low-severity, but it is a latent threading assumption. | detected | Construct a sub-transaction chain and lock from two threads simultaneously; TSan may flag the unlocked read of `isSubTransaction_`. | — |
| MEM-016 | src/rogue/interfaces/memory/Block.cpp | 880 | logic | low | `setByteArrayPy` error message (line 880) says `"Block::setByteArray"` instead of `"Block::setByteArrayPy"` — mismatched error source name that will appear in user-facing exceptions and confuse debugging. | detected | Trigger the error path; check exception message. | — |

---

## Block.cpp Region Coverage Notes

**Region 1 — Marshalling (lines 660-760):** Covered. `setBytes` (line 652), `getBytes` (line 726), variable→blockData_ copy chain reviewed. Findings: MEM-005 (fastByte_ potential overrun), MEM-006 (malloc null deref). The core memcpy chain at lines 667, 684, 709, 745, 753 was inspected; bounds are enforced through `fastByte_` indexing derived from `shiftOffsetDown` initialization in Variable.cpp. The primary risk is the list-variable stride alignment gap (MEM-005).

**Region 2 — Float/int coercion (lines 1700-1920):** Covered. Reviewed all float format converters: `floatToHalf`/`halfToFloat` (1737-1791), `floatToFloat8`/`float8ToFloat` (1793-1853), `floatToBFloat16`/`bfloat16ToFloat` (1855-1875), `floatToTensorFloat32`/`tensorFloat32ToFloat` (1880-1896), `floatToFloat6`/`float6ToFloat` (1901-1948), `floatToFloat4`/`float4ToFloat` (1953-2001). Findings: MEM-008 (no bug, design correct), MEM-009 (NaN bypasses range check, affects all float set functions).

**Region 3 — State machine / remainder (lines 1-660 and 2002-3290):** Covered. Transaction start/check/wait state machine reviewed (lines 175-416). Type coercion dispatch (setUInt/Int/Bool/String/Float/Double/Fixed, lines 919-3290) reviewed — all delegate to setBytes/getBytes which hold `mtx_`. Findings: MEM-007 (VLA stack risk in addVariables), MEM-010 (exception-handling fragility), MEM-013 (anyBits logic bug in Master.cpp, affects verify mask evaluation), MEM-014 (undocumented lock order).

---

## Cross-Subsystem References

- MEM-001/MEM-002 are the ROADMAP SC-1 mandated `classMtx_` hotspots in Slave.cpp and Transaction.cpp respectively. Both use the same raw lock/unlock pattern as CONCERNS.md §Logging Mutex Manual Lock Pattern (Logging.cpp). Consolidation plan should normalize severity across these three identical patterns (all `high`).
- MEM-003/MEM-004 (`threadEn_` non-atomic) matches the pattern fixed in stream/Fifo (`dropFrameCnt_`, `threadEn_`) per CONCERNS.md and commit `b1a669c96`. TcpClient/TcpServer did not receive that fix.
- MEM-011 (sub-transaction completion race) affects Hub.cpp splitting logic; cross-reference PROTO subsystem review for RSSI sub-transaction paths.
- MEM-013 (anyBits logic bug) affects the variable-overlap verification check in `Block::addVariables` (lines 498-507, 543-550); wrong `false` results from `anyBits` can silently allow overlapping variable bit mappings to pass validation.
