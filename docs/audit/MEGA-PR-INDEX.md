# Phase 4 Mega-PR Index

**Generated:** 2026-04-24
**Phase:** 04 — Surgical Fixes
**Branch:** hunt-for-red-october
**Phase-start SHA:** `4cfdbda29c763f8420a49ee6ecf214152988e5fd`
**Phase-end SHA:** `5dac59bde5177d1b95857c31fd7b7eeda00da29f`
**Total fix commits:** 10

Source data: `git log --grep="^fix(" hunt-for-red-october --not 4cfdbda29c763f8420a49ee6ecf214152988e5fd`, cross-referenced with `docs/audit/REPRODUCIBLE.md` for evidence-file paths.

Schema per row: `| REPRODUCIBLE ID | File(s) | Lines | Change Class | Commit SHA | Evidence File |` (D-13).

Fix Class distribution: atomic-conversion=2, memory-lifetime=6, other=2 (3 sections — FIX-03 limit: <=4, PASS).

## Atomic Conversion

| REPRODUCIBLE ID | File(s) | Lines | Change Class | Commit SHA | Evidence File |
|-----------------|---------|-------|--------------|------------|---------------|
| STREAM-003 | include/rogue/interfaces/stream/TcpCore.h | 74-81 | atomic-conversion | `ad5d184b2acb43b461b76d4636f7324ae13223f9` | [tsan](./evidence/tsan/STREAM-003.log) |
| PROTO-UDP-001 | include/rogue/protocols/udp/Core.h | 76-83 | atomic-conversion | `937d39e61a2a9e5506b3d5278dae11c3edcc6339` | [tsan](./evidence/tsan/PROTO-UDP-001.log) |

## Memory Lifetime

| REPRODUCIBLE ID | File(s) | Lines | Change Class | Commit SHA | Evidence File |
|-----------------|---------|-------|--------------|------------|---------------|
| HW-CORE-007 | src/rogue/hardware/axi/AxiStreamDma.cpp | 207-216 | memory-lifetime | `dc41ed5cde8fe7b3b913f08ceb7a4520f59d6985` | [asan](./evidence/asan/HW-CORE-007.log) |
| HW-CORE-010 | src/rogue/hardware/MemMap.cpp | 61-73 | memory-lifetime | `893551b798337bbe98d0d7e26607b65d2af64a7b` | [asan](./evidence/asan/HW-CORE-010.log) |
| HW-CORE-011 | src/rogue/hardware/axi/AxiMemMap.cpp | 61-70 | memory-lifetime | `800373367a43b290a7486869fe2aaa776ac78b76` | [asan](./evidence/asan/HW-CORE-011.log) |
| HW-CORE-017 | src/rogue/utilities/StreamUnZip.cpp | 96-105 | memory-lifetime | `3a8e137f81179ff3e41491570d0e0b3fdcc69fcb` | [tsan](./evidence/tsan/HW-CORE-017.log) |
| MEM-005 | src/rogue/interfaces/memory/Block.cpp | 680-693 | memory-lifetime | `a16bc16019c79c195c0ba406506ba16acd00b44f` | [tsan](./evidence/tsan/MEM-005.log) |
| MEM-006 | src/rogue/interfaces/memory/Block.cpp | 664-675 | memory-lifetime | `b0080df1be5fa3fee2bb93c32036cacbcc3aa7a4` | [tsan](./evidence/tsan/MEM-006.log) |

## Other

Additional PROTO-UDP-001 fixes beyond the canonical `atomic-conversion` change — destructor-ordering / teardown-primitive hardening that improved the UDP teardown discipline but did not fully silence the downstream `test_stress_udp_threaden` SIGABRT (see `REPRODUCIBLE.md` §Phase 4 Partial Fix Notes and `.planning/phases/04-surgical-fixes/04-02-MIDPHASE-RERUN.md` §0.B). The commit-body `Fix Class:` labels are `destructor-ordering` and `destructor-ordering (continuation)`; mapped to `other` for FIX-03 index purposes.

| REPRODUCIBLE ID | File(s) | Lines | Change Class | Commit SHA | Evidence File |
|-----------------|---------|-------|--------------|------------|---------------|
| PROTO-UDP-001 | src/rogue/protocols/udp/Client.cpp, src/rogue/protocols/udp/Server.cpp | 111-131 | other | `6e79e9afafc2cc36e5f5f077a0ac9a2980825310` | [tsan](./evidence/tsan/PROTO-UDP-001.log) |
| PROTO-UDP-001 | src/rogue/protocols/udp/Client.cpp, src/rogue/protocols/udp/Server.cpp | 66-131 | other | `f841be6a90385dd77d49bd22489578b133a1ff84` | [tsan](./evidence/tsan/PROTO-UDP-001.log) |

## Summary

- **Total fix commits:** 10
- **Fix Class distribution:** atomic-conversion=2, memory-lifetime=6, other=2, raii-lock-guard=0, gil-ordering=0, python-layer=0
- **FIX-03 compliance:** 3 Fix-Class sections present (requirement: <=4) — PASS
- **Every row has a populated 40-char SHA:** verified; 10 rows, 10 SHAs, 1-to-1 with `git log --grep='^fix('` on `hunt-for-red-october` since `4cfdbda29`
- **Phase 5 SHIP-01 note:** SHIP-01 lifts the three `##` tables above verbatim into the mega-PR body. The PROTO-UDP-001 entries span three commits (`937d39e61`, `6e79e9afa`, `f841be6a9`) which must be cherry-picked as a contiguous chain for Phase 5 VERIFY-01; the REPRODUCIBLE.md "Phase 4 Partial Fix Notes" section documents why positive-SIGABRT-cleared evidence is not claimed for this row this milestone.
- **Phase 4 D-24 Class B closure:** 58 coverage-gap DETECTED IDs transitioned `detected -> detected-only` in commit `5dac59bde` (the DETECTED.md consolidation commit that immediately precedes this one). Those rows are out of FIX-03 scope — detected-only findings are not fixed this milestone (per PROJECT.md Out of Scope + D-05 variant / D-24 Class B carve-out).
- **Phase 4 D-24 Class A closure:** HW-CORE-007 / HW-CORE-010 / HW-CORE-011 fixed under Tier 2 code-review disposition (per Plan 04-06 `04-06-TIER-DECISION.md` and Phase 4 CONTEXT.md D-06/D-07). DETECTED.md Status stays `detected`; REPRODUCIBLE.md CI Signal annotated with the ASan infra-blocked disposition; positive ASan evidence is not claimed this milestone.
