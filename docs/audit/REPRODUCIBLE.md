# REPRODUCIBLE — Phase 3 Triage Outcome (Phase 4 Fix Checklist)

**Branch:** hunt-for-red-october
**Phase:** 03 — Triage & Reproducible List
**Generated:** 2026-04-23

## Preamble (D-08)

- **Run SHAs (hunt-for-red-october):**
  - ci-tsan canonical-run commit SHA: `e333f19f4637615ca1cd790fa6549b45f6ef56cf`
    (commit: `sanitizer: expand tsan.supp with noise entries from first CI run`, 2026-04-24)
  - ci-asan canonical-run commit SHA: `8e0dfc2722bf223c947084c7cddf689f1136ab5b`
    (commit: `fix(03-04): use ASAN_OPTIONS log_path to preserve error reports past SIGABRT`, 2026-04-24)
- **Workflow runs:**
  - ci-tsan run 24887983787 (date: 2026-04-24, duration: 8m8s) — GH artifacts retained 14 days; full log archived at `.planning/audit/evidence/tsan-full/ci-tsan-24887983787.log.gz`
  - ci-asan run 24889708073 (date: 2026-04-24) — full log archived at `.planning/audit/evidence/asan-full/ci-asan-24889708073.log.gz`
- **tsan.supp blob SHA at canonical TSan run:** `75e447967f516ee1a3b6eafe4189a00fcce0e3a6`
- **Total Phase 3 infra fix commits landed (Waves 2, 3, 4):** 14
- **Summary counts:**
  - reproducible_total: 5
  - Fix Class breakdown: atomic-conversion=2 (STREAM-003, PROTO-UDP-001), memory-lifetime=3 (HW-CORE-017, MEM-005, MEM-006)
  - detected-only-from-triage: 0 (HW-CORE-007, HW-CORE-010, HW-CORE-011 remain `detected` pending ASan re-run — see "Held for Re-run" section)

### Evidence Pivot: Why There Are No TSan race: or ASan ERROR: Blocks

**TSan pivot (Wave 2):** The canonical ci-tsan run (24887983787) produced **0 `WARNING: ThreadSanitizer: data race` blocks**. The targeted bugs cause the process to abort before the TSan race reporter fires: `threadEn_` races cause SIGABRT in the destructor chain (PROTO-UDP-001) or exercise code paths that fail test assertions before TSan can interpose the racy accesses (STREAM-003, MEM-005, MEM-006, HW-CORE-017). All 5 reproducible rows use pytest FAILED (5/5) or SIGABRT as the CI signal, per the Wave 2/3 pivot strategy ratified at plan 03-03.

**ASan pivot:** The canonical ci-asan run (24889708073) produced **0 `ERROR: AddressSanitizer:` blocks**. Root cause: rogue.so is linked with `-fsanitize=address`, which pulls libasan.so as a `DT_NEEDED` entry. Any secondary libasan.so load (via ldconfig or LD_PRELOAD) causes `real___cxa_throw` to be set `NULL` on the second ASan initializer. The first C++ exception throw then triggers `ASan CHECK fail: real___cxa_throw != 0` and aborts the process. This CHECK failure bypasses `halt_on_error=0` by design — CHECK failures are always fatal in the ASan runtime. Seven ci-asan.yml infra-fix commits (102dbafd2..4cfdbda29) did not resolve the underlying interception; the fix requires a link-time change to rogue.so (`-shared-libasan` or LD_PRELOAD ordering before Python starts), which is beyond Phase 3 scope.

Consequently: three DETECTED IDs (MEM-005, MEM-006, HW-CORE-017) are ratified via TSan evidence only. Their ASan evidence files (`./evidence/asan/<ID>.log`) document the infra gap, not genuine ASan errors. Three DETECTED IDs (HW-CORE-007, HW-CORE-010, HW-CORE-011) are held for re-run pending an ASan infrastructure fix — they are NOT declared detected-only per D-13 (which requires a clean run, not an infra-blocked run).

---

## Reproducible Rows

| ID | File | Lines | DETECTED Class | Severity | CI Signal | Triggering Script | Log Snippet | Evidence File | Fix Class | Fixed in commit |
|----|------|-------|----------------|----------|-----------|-------------------|-------------|---------------|-----------|-----------------|
| STREAM-003 | include/rogue/interfaces/stream/TcpCore.h | 76 | threading | high | TSan test-FAIL (5/5) | stress_atomic_conversions.py | `FFFFF` — test_stress_tcpcore_threaden FAIL × 5; threadEn_ race on TcpCore dtor/runThread | [tsan](./evidence/tsan/STREAM-003.log) | atomic-conversion | ad5d184b2acb43b461b76d4636f7324ae13223f9 |
| PROTO-UDP-001 | src/rogue/protocols/udp/Client.cpp, src/rogue/protocols/udp/Server.cpp | 113-126, 107-119 | threading | medium | TSan SIGABRT (still reproducing post-partial-fix, different proximate cause — see §Phase 4 Partial Fix Notes) | stress_atomic_conversions.py | `Fatal Python error: Aborted` — test_stress_udp_threaden; UDP dtor threadEn_ race causes SIGABRT | [tsan](./evidence/tsan/PROTO-UDP-001.log) | atomic-conversion | f841be6a9 (partial — see §Phase 4 Partial Fix Notes) |
| HW-CORE-017 | src/rogue/utilities/StreamUnZip.cpp | 98-101 | memory | medium | TSan test-FAIL (5/5); ASan infra-blocked (no capture) | stress_asan_memory.py | `FFFFFFFFFF` — test_stress_streamunzip_truncated FAIL × 5; iterator out-of-bounds on truncated bzip2 input | [tsan](./evidence/tsan/HW-CORE-017.log), [asan](./evidence/asan/HW-CORE-017.log) | memory-lifetime | 3a8e137f81179ff3e41491570d0e0b3fdcc69fcb |
| MEM-005 | src/rogue/interfaces/memory/Block.cpp | 660-724 | memory | medium | TSan test-FAIL (5/5); ASan infra-blocked (no capture) | stress_asan_memory.py | `FFFFFFFFFF` — test_stress_block_setbytes_malloc FAIL × 5; concurrent Value.set() races on Block; memcpy overrun path | [tsan](./evidence/tsan/MEM-005.log), [asan](./evidence/asan/MEM-005.log) | memory-lifetime | a16bc16019c79c195c0ba406506ba16acd00b44f |
| MEM-006 | src/rogue/interfaces/memory/Block.cpp | 660-760 | memory | low | TSan test-FAIL (5/5); ASan infra-blocked (no capture) | stress_asan_memory.py | `FFFFFFFFFF` — test_stress_block_setbytes_malloc FAIL × 5; malloc null-deref path in setBytes exercised concurrently | [tsan](./evidence/tsan/MEM-006.log), [asan](./evidence/asan/MEM-006.log) | memory-lifetime | b0080df1be5fa3fee2bb93c32036cacbcc3aa7a4 |
| HW-CORE-007 | src/rogue/hardware/axi/AxiStreamDma.cpp | 192-215 | memory | medium | ASan infra-blocked; fix justified by code review (fd leak on exception path); Phase 5 VERIFY-01 evidence is ci-asan.yml green (no regression), not a positive ERROR-then-clean comparison | stress_asan_memory.py | (code review only — see fix commit body; ASan infra-blocked per Phase 3 D-24 + Phase 4 D-06 Tier 2) | (inline in commit body — no separate log file under TIER=2 per Phase 4 revision pass Blocker 4) | memory-lifetime | dc41ed5cde8fe7b3b913f08ceb7a4520f59d6985 |
| HW-CORE-010 | src/rogue/hardware/MemMap.cpp | 63-66 | memory | medium | ASan infra-blocked; fix justified by code review (fd leak on exception path); Phase 5 VERIFY-01 evidence is ci-asan.yml green (no regression), not a positive ERROR-then-clean comparison | stress_asan_memory.py | (code review only — see fix commit body; ASan infra-blocked per Phase 3 D-24 + Phase 4 D-06 Tier 2) | (inline in commit body — no separate log file under TIER=2 per Phase 4 revision pass Blocker 4) | memory-lifetime | 893551b798337bbe98d0d7e26607b65d2af64a7b |

---

## NEW Findings Ratified in Wave B (D-20)

None. Zero `WARNING: ThreadSanitizer: data race` blocks were emitted in the canonical TSan run, and zero `ERROR: AddressSanitizer:` blocks were captured in the canonical ASan run. All pytest FAIL and SIGABRT signals map cleanly to existing DETECTED IDs via script docstrings. No D-20 action required.

---

## Rejections — Detected-Only Dispositions (staged for 03-06)

None in this wave. The three ASan-primary rows that produced zero signal (HW-CORE-007, HW-CORE-010, HW-CORE-011) are NOT classified as detected-only because the zero signal is an infrastructure artifact (ASan double `__cxa_throw` interception), not a genuine clean run. Per D-13: detected-only disposition requires a clean run, not an infra-blocked run.

---

## Rejections — Held for Re-run (D-02)

**SC-2 carve-out reference:** The 3 ASan-infra-blocked rows listed below (HW-CORE-007, HW-CORE-010, HW-CORE-011) are carved out of SC-2's `detected-only` requirement by D-24 in `.planning/phases/03-triage-reproducible-list/03-CONTEXT.md` (ratified 2026-04-24). Their `Status: detected` in DETECTED.md is intentional per D-13 (clean run required for `detected-only`). See `.planning/phases/03-triage-reproducible-list/03-VERIFICATION.md` "SC-2 Closure via D-24 Carve-Out" section for the full closure narrative.

**Rejection reason for all 6 rows:** ci-asan.yml infra fixes (commits `102dbafd2`..`4cfdbda29`, 7 iterations) did not resolve the double `__cxa_throw` interception. Root cause: rogue.so is linked with `-fsanitize=address` (pulls libasan.so as `DT_NEEDED`); any secondary libasan.so load via ldconfig or LD_PRELOAD causes `real___cxa_throw` to be set `NULL` on the second ASan init. The first C++ exception throw triggers `ASan CHECK fail: real___cxa_throw != 0` and aborts the process before target app code executes meaningfully. This is non-suppressible by `halt_on_error=0` (CHECK failures bypass halt_on_error by design). Hold until a rogue.so link-time fix (`-shared-libasan` or LD_PRELOAD ordering before Python starts).

| DETECTED ID | File | Severity | Draft Signal | Also-in-TSan-draft? | Hold Reason | Proposed re-run parameters |
|-------------|------|----------|--------------|---------------------|-------------|---------------------------|
| HW-CORE-007 | src/rogue/hardware/axi/AxiStreamDma.cpp | medium | ASan CHECK-failure (infra artifact, not genuine memory error) | no | No genuine ASan ERROR block; infra aborts before memory checks; no TSan signal | After ci-asan.yml link-time fix: re-run stress_asan_memory.py, expect `ERROR: AddressSanitizer: heap-use-after-free` or fd-leak report |
| HW-CORE-010 | src/rogue/hardware/MemMap.cpp | medium | ASan infra-blocked (test not reached) | no | Pytest process killed before this test ran; zero coverage of any kind | After ci-asan.yml fix: re-run; expect exception-path ASan error |
| HW-CORE-011 | src/rogue/hardware/axi/AxiMemMap.cpp | medium | ASan infra-blocked (test not reached) | no | Pytest process killed before this test ran; zero coverage of any kind | After ci-asan.yml fix: re-run; expect exception-path ASan error |
| MEM-005 | src/rogue/interfaces/memory/Block.cpp | medium | ASan infra-blocked (test not reached) | yes — RATIFIED via TSan signal | ASan component held; TSan signal already ratified (Row 4 above) | After ci-asan.yml fix: re-run stress_asan_memory.py; expect `ERROR: AddressSanitizer: heap-buffer-overflow` in Block::setBytes |
| MEM-006 | src/rogue/interfaces/memory/Block.cpp | low | ASan infra-blocked (test not reached) | yes — RATIFIED via TSan signal | ASan component held; TSan signal already ratified (Row 5 above) | After ci-asan.yml fix: re-run; expect `ERROR: AddressSanitizer:` NULL-deref in Block::setBytes malloc path |
| HW-CORE-017 | src/rogue/utilities/StreamUnZip.cpp | medium | ASan infra-blocked (test not reached) | yes — RATIFIED via TSan signal | ASan component held; TSan signal already ratified (Row 3 above) | After ci-asan.yml fix: re-run stress_asan_memory.py; expect `ERROR: AddressSanitizer: heap-buffer-overflow` in StreamUnZip::acceptFrame |

**Note on MEM-005, MEM-006, HW-CORE-017:** These three IDs appear in both the TSan draft (ratified in Reproducible Rows above) and the ASan held-for-rerun table. Per D-06, each DETECTED ID gets one REPRODUCIBLE.md row — the TSan evidence is sufficient to land the row. The ASan evidence files document the infra gap. When the ci-asan.yml fix lands, the existing REPRODUCIBLE.md rows for these IDs should have their CI Signal cell updated to add the ASan confirmation.

---

## Notes

- REPRODUCIBLE.md row count (5) is a strict subset of DETECTED.md's triage-candidate set (66 rows covered by cluster scripts). The small count reflects Phase 3's signal reality: PROTO-UDP-001's SIGABRT killed the pytest process before 9 of 11 cluster scripts ran, leaving the corresponding IDs without coverage this wave.
- Scripts not reached due to PROTO-UDP-001 SIGABRT: stress_bsp_gil.py, stress_fileio_fd_race.py, stress_gil_wrong_direction.py, stress_memory_sub_transaction.py, stress_python_update_worker.py, stress_raw_lock_unlock.py, stress_rssi_state_races.py, stress_shared_ptr_null_deref.py, stress_stream_counters.py. These are candidates for 03-07 (D-14 soak escape hatch) after PROTO-UDP-001 is fixed.
- Evidence files under `.planning/audit/evidence/` are durable (D-03/D-05) and ship in the mega-PR (SHIP-01/SHIP-02).
- "Fixed in commit" column is populated by Phase 4 as each fix commit lands; Phase 5 verification confirms.
- PROTO-UDP-001: despite medium severity rating, this is the highest-priority fix in the atomic-conversion class because its SIGABRT blocked 9 downstream cluster scripts from producing any signal this phase.
- The 58 coverage-gap DETECTED IDs covered by the 9 unreached cluster scripts listed above are carved out of SC-2's `detected-only` requirement by D-24 (ratified 2026-04-24). Their Phase 4 obligations — re-run after PROTO-UDP-001 fix lands or classify via code-review-driven inspection — are recorded in `.planning/phases/03-triage-reproducible-list/03-VERIFICATION.md` "SC-2 Closure via D-24 Carve-Out" section.

## Phase 4 Partial Fix Notes

### PROTO-UDP-001 — partial fix landed this milestone

Phase 4 landed three surgical commits that improve the UDP teardown discipline:

- `937d39e61` — `fix(PROTO-UDP-001): convert UDP Core threadEn_ to std::atomic<bool>` (the original Phase 4 plan shape)
- `6e79e9afa` — `fix(PROTO-UDP-001): extend destructor join ordering — shutdown+GilRelease+delete` (Path A — adds GilRelease, unblock-before-join, delete thread_, mirrors `Fifo::~Fifo()` precedent PR #1191 `b1a669c96`)
- `f841be6a9` — `fix(PROTO-UDP-001): use close() not shutdown() to unblock UDP recvfrom, add SO_REUSEADDR` (Path A.1 — switches to portable UDP unblock primitive, adds rebind safety)

**The original race the row describes — the UDP worker outliving its owning object on teardown — is closed.** Post-fix ci-tsan stack traces show the worker C thread handle as `0x0` (joined / destroyed), not the pre-fix `0x7f98…` (alive). That is a real, verifiable improvement to the codebase and to the teardown contract.

**However, the ci-tsan reproducer `stress_atomic_conversions.py::test_stress_udp_threaden` still produces a SIGABRT at the same test position** with a different proximate cause (two concurrent Python workers in Server constructor + Client destructor, main in `threading.py:994 Thread.start()`). The new abort fires before any single UDP `cycle()` iteration completes and is not caused by the teardown race the original row describes. Diagnosing the new abort exceeded the D-02 two-run retry budget for the mid-phase canonical re-run. D-22 escalation (Phase 3) triggered automatic pivot to D-24 Class B Path B: Phase 4 does not claim to fully resolve PROTO-UDP-001 this milestone, and the 9 previously-unreached cluster scripts remain out of reach for SC-2 coverage.

**Phase 5 verification implications:** the "Fixed in commit" cell (`f841be6a9`) marks the HEAD of the landed improvement chain. Cherry-pick verification MUST pull the full range `937d39e61..f841be6a9` (3 commits). The row MUST NOT be treated as fully closed for SC-2 graduation — this limitation is recorded in `04-02-MIDPHASE-RERUN.md` §0 and `04-VERIFICATION.md` (once written).

**Evidence trail:**
- Pre-fix: `docs/audit/evidence/tsan-full/ci-tsan-24908065882.log.gz` (worker alive, pre-Path-A)
- Post-Path-A: `docs/audit/evidence/tsan-full/ci-tsan-24909162566.log.gz` (worker joined, new SIGABRT pattern)
- Post-Path-A.1 final: `docs/audit/evidence/tsan-full/ci-tsan-24909791467.log.gz` (same new SIGABRT pattern, D-02 budget exhausted)
