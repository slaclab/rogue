#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Title      : ROGUE Perf Metric Tier Registry
# ----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
# ----------------------------------------------------------------------------

"""Declarative metric to tier/direction/comparison/calibration-pairing map,
shared as a flat sibling import by the tests/perf/ harness (the collector)
and scripts/perf_campaign_report.py (the analyzer), so the two can never
disagree about a metric's tier or comparison rule. Not extending
scripts/perf_data.py's `_metric_descriptor`: that function is kept scoped
to exactly the two pre-existing published fields, `avg_ns` and
`throughput_mb_s`, so widening the tier-aware metric surface here never
changes that function's own contract.
"""

from __future__ import annotations

from typing import Any

REGISTRY_VERSION = 1

TIER_1 = 1
TIER_2 = 2
TIER_3 = 3

DIRECTION_LOWER_IS_BETTER = "lower_is_better"
DIRECTION_HIGHER_IS_BETTER = "higher_is_better"
DIRECTION_INVARIANT = "invariant"

COMPARISON_BIT_IDENTICAL = "bit_identical"
COMPARISON_DISPERSION_BAND = "dispersion_band"
COMPARISON_NON_GATING = "non_gating"

CALIBRATION_NONE = "none"

# The four independently measured components env_fingerprint.collect_calibration_vector()
# returns, each reduced to its own median across repeated measurements so one outlier sample
# cannot swing the calibration figure. A non-CALIBRATION_NONE calibration_pairing must name
# one of these; validate_registry() enforces it so a typo in a pairing can never silently
# resolve to CALIBRATION_NONE's "no normalization" semantics.
CALIBRATION_COMPONENTS: tuple[str, ...] = ("alu", "memcpy", "syscall", "tsc")

PERF_SOFTWARE_EVENTS_EXCLUSION_REASON = (
    "All 14 `perf` events Phase 2 probed (docs/plans/perf-ci-hardening/CAPABILITY-MATRIX.md, "
    "Perf events table) are excluded from this registry entirely, not placed at Tier 2. The 8 "
    "software events are gating_eligible: false across all 20 probe runs because they count "
    "only after a `sudo sysctl` lowering of kernel.perf_event_paranoid, a privilege a gating "
    "job cannot depend on identically across every contributor pull request and every fork. "
    "The 6 hardware events were not-supported in both the default and lowered paranoid states "
    "across all 20 runs, so no calibrated deterministic reading is available from them on this "
    "runner fleet at all. A software or hardware event is admitted to Tier 1 only where it is "
    "proven deterministic and is otherwise excluded rather than placed at a lower tier, so "
    "this rule excludes every one of the 14 rather than registering any at Tier 2."
)

# The exact seven named metric families this registry must account for: "syscalls per N
# operations" (renamed rogue_issued_io_calls, since the transaction path issues none and the
# metric is Rogue's own I/O call sites, not process syscalls), "buffer copy count and total
# bytes copied", "heap allocations and peak bytes", "Frame and Buffer construction counts",
# "mutex acquisitions", "Python to C++ boundary crossings", and "bytes-on-wire per payload
# byte". validate_registry() enforces that each of these seven is either the `family` of at
# least one registered metric, or is recorded in UNCOVERED_FAMILIES with a reason -- never
# silently absent from both.
REQUIRED_METRIC_FAMILIES: tuple[str, ...] = (
    "mutex_acquisitions",
    "buffer_copies",
    "heap_allocations",
    "frame_buffer_construction",
    "rogue_issued_io_calls",
    "python_cpp_crossings",
    "bytes_on_wire",
)

# The coverage gap this work cannot close: the transaction path runs entirely in-process
# against rogue.interfaces.memory.Emulate (tests/perf/test_variable_rate_perf.py) and issues
# no I/O of any kind, so bytes_on_wire_ratio (registered below, scoped to the stream-path
# benchmarks only) has no transaction-path counterpart. Recorded here explicitly rather than
# left for a reader to infer.
UNCOVERED_FAMILIES: dict[str, str] = {
    "bytes_on_wire": (
        "not covered on the transaction path: the transaction benchmarks "
        "(tests/perf/test_variable_rate_perf.py) run entirely in-process against "
        "rogue.interfaces.memory.Emulate and put no bytes on any wire. bytes_on_wire_ratio is "
        "registered and scoped to the stream-path benchmarks only."
    ),
}

# Every rogue getter a Tier 1 `source` field is permitted to name: rogue.PerfCounters'
# process-wide getters this work adds, declared here so the registry and the eventual C++
# symbol never drift apart even for the getters a later change lands, plus the existing
# per-object getters (Pool, Slave, the batcher combiners, the packetizer cores, Prbs) that
# were already present and already bound to Python before this work started.
KNOWN_TIER_1_SOURCES: tuple[str, ...] = (
    "rogue.PerfCounters.getBufferCopyBytes",
    "rogue.PerfCounters.getBufferCopyCount",
    "rogue.PerfCounters.getFrameCreateCount",
    "rogue.PerfCounters.getFrameLockCount",
    "rogue.PerfCounters.getGilAcquireCount",
    "rogue.PerfCounters.getGilReleaseCount",
    "rogue.PerfCounters.getIoBytes",
    "rogue.PerfCounters.getIoCallCount",
    "rogue.PerfCounters.getScopedGilCount",
    "rogue.PerfCounters.getTransactionCreateCount",
    "rogue.PerfCounters.getTransactionLockCount",
    "rogue.PerfCounters.getTransactionRequestBytes",
    "rogue.PerfCounters.getTransactionRequestCount",
    "rogue.interfaces.stream.Pool.getAllocPeakBytes",
    "rogue.interfaces.stream.Pool.getAllocTotalBytes",
    "rogue.interfaces.stream.Pool.getAllocTotalCount",
    "rogue.interfaces.stream.Slave.getByteCount",
    "rogue.interfaces.stream.Slave.getFrameCount",
    "rogue.protocols.batcher.CombinerV1.getCount",
    "rogue.protocols.batcher.CombinerV2.getCount",
    "rogue.protocols.packetizer.Core.getDropCount",
    "rogue.protocols.packetizer.CoreV2.getDropCount",
    "rogue.utilities.Prbs.getRxBytes",
    "rogue.utilities.Prbs.getRxCount",
    "rogue.utilities.Prbs.getRxErrors",
    "rogue.utilities.Prbs.getTxBytes",
    "rogue.utilities.Prbs.getTxCount",
    "rogue.utilities.Prbs.getTxErrors",
)

_VALID_TIERS = (TIER_1, TIER_2, TIER_3)
_VALID_DIRECTIONS = (DIRECTION_LOWER_IS_BETTER, DIRECTION_HIGHER_IS_BETTER, DIRECTION_INVARIANT)
_VALID_COMPARISONS = (COMPARISON_BIT_IDENTICAL, COMPARISON_DISPERSION_BAND, COMPARISON_NON_GATING)
_VALID_CALIBRATION_PAIRINGS = (CALIBRATION_NONE,) + CALIBRATION_COMPONENTS

_REQUIRED_KEYS = (
    "tier", "direction", "comparison", "calibration_pairing", "unit", "family", "source", "benchmarks",
)

# The transaction path's seven test_variable_rate_perf.py operations: each gets its own
# counter snapshot pair, its own repeat loop, its own dispersion figure, and its own tier.
TRANSACTION_BENCHMARKS: tuple[str, ...] = (
    "linkedGetRate",
    "linkedSetRate",
    "localGetRate",
    "localSetRate",
    "remoteGetRate",
    "remoteSetNvRate",
    "remoteSetRate",
)

# The six stream-path benchmark identities the other four tests/perf/ stream modules emit
# (udp_packetizer publishes four separate records, one per version/jumbo combination).
STREAM_BENCHMARKS: tuple[str, ...] = (
    "fifo_perf",
    "stream_bridge_perf",
    "udp_packetizer_perf_v1_jumbo",
    "udp_packetizer_perf_v1_std",
    "udp_packetizer_perf_v2_jumbo",
    "udp_packetizer_perf_v2_std",
)

# test_block_gil_contention_perf.py's single benchmark.
GIL_BENCHMARKS: tuple[str, ...] = (
    "block_gil_contention_drain",
)

# Benchmark identities that exist purely to close a metric-family coverage gap: the families
# they measure need an object none of the five pre-existing tests/perf/ modules holds (a
# Python-readable rogue.interfaces.stream.Pool/Slave mirroring its own real allocations, or a
# constructed batcher CombinerV1/V2). tests/perf/test_pool_alloc_perf.py and
# tests/perf/test_batcher_combine_perf.py emit these identities.
COVERAGE_BENCHMARKS: tuple[str, ...] = (
    "batcher_combine_perf",
    "pool_alloc_perf",
)

# The full 16-benchmark universe the five original tests/perf/ modules plus the two
# coverage-gap-closure modules cover; every metric below draws its `benchmarks` tuple from
# this set, and every element of this set appears in at least one metric's `benchmarks` tuple
# (enforced by tests/utilities/test_perf_tier_registry.py).
ALL_BENCHMARKS: tuple[str, ...] = TRANSACTION_BENCHMARKS + STREAM_BENCHMARKS + GIL_BENCHMARKS + COVERAGE_BENCHMARKS


class RegistryError(Exception):
    """Raised when METRICS is malformed: a duplicate name, an unrecognized
    tier/direction/comparison/calibration-pairing value, a missing required
    key, a Tier 1 source naming a getter outside KNOWN_TIER_1_SOURCES,
    or a family named in REQUIRED_METRIC_FAMILIES absent from both the registry and
    UNCOVERED_FAMILIES. Raised at import time so a duplicate definition can
    never silently resolve to the later one winning."""


def _tier1_source_tokens(source: str) -> tuple[str, ...]:
    """Split a Tier 1 `source` field on ' / ' for metrics whose count is the
    union of two getters (for example a family whose Python and C++ sides
    share one counter name, such as `combiner_count`)."""
    return tuple(token.strip() for token in source.split(" / ") if token.strip())


# One (name, descriptor) pair per metric, kept as a sequence rather than a dict literal so a
# duplicate name is a duplicate list entry validate_registry can detect, instead of a
# duplicate dict key Python would have already silently merged before any validation ran.
#
# POST-CAMPAIGN BINDING TIER UPDATE, the second auditable step in reconciling this registry's
# candidate tiers against measured evidence, citing
# docs/plans/perf-ci-hardening/CAMPAIGN-REPORT.md's "Cross-CPU-model invariance" section,
# generated from the 24-run real campaign against perf-harness/campaign-v2, tree hash
# 6b74f79118161d744d1969808ef3020a3844a570, 4 observed CPU models). Every Tier 1 candidate the
# invariance section recorded as `demoted-to-tier-2` or `demoted-to-tier-2-within-run` is
# demoted here to TIER_2 with `comparison` changed to COMPARISON_DISPERSION_BAND (a metric no
# longer bit-identical needs the dispersion-band comparison every other Tier 2 metric already
# uses: a Tier 1 metric with a tolerance is really a Tier 2 metric with a tight threshold.
# `direction` stays DIRECTION_INVARIANT: these remain plain counts, only no longer provably
# deterministic across CPU models. Fourteen metrics demoted: buffer_copy_bytes,
# buffer_copy_count, bytes_on_wire_ratio, frame_create_count, frame_lock_acquisitions,
# gil_acquire_count, gil_release_count (the GIL-crossing nondeterminism this reflects:
# Root's own background threads cross the GIL independently of pollEn), io_bytes,
# io_call_count, scoped_gil_count, transaction_create_count, transaction_lock_acquisitions,
# transaction_request_bytes, transaction_request_count.
#
# Every Tier 1 candidate the invariance section recorded `bit-identical` across all 4 observed
# models stays at TIER_1 unchanged: core_drop_count, prbs_rx_bytes, prbs_rx_count,
# prbs_rx_errors, prbs_tx_bytes, prbs_tx_count, prbs_tx_errors.
#
# Six Tier 1 candidates the invariance section recorded `not-recorded` (no accepted record ever
# measured them at all) are left at their candidate TIER_1 unchanged, on the principle that an
# unproven candidate must not be promoted on no evidence: combiner_count,
# pool_alloc_peak_bytes, pool_alloc_total_bytes, pool_alloc_total_count, slave_byte_count,
# slave_frame_count. This is not evidence these six are genuinely bit-identical; it is the
# absence of any evidence at all, since no tests/perf/ module can currently read a real
# rogue.interfaces.stream.Pool/Slave allocation or the batcher combiner's count: this is the
# heap_allocations/slave_frame_accounting/batcher_combining coverage gap, unresolved as of this
# registry update. See HARNESS-SETUP.md's coverage accounting and requirement reconciliation
# for these seven metric families' honest status.
#
# SECOND POST-CAMPAIGN BINDING TIER UPDATE, citing the same report's "Cross-CPU-model
# invariance" section regenerated against the recampaign against perf-harness/campaign-v3, tree
# hash e9e53cdb0f493b1faf1f1d11c4eb1fdbc6144b03, 25 records (24 clean plus 1 injected-load
# demonstration excluded from every invariance figure), 3 observed CPU models (AMD EPYC 7763
# 64-Core Processor, AMD EPYC 9V74 80-Core Processor, INTEL(R) XEON(R) PLATINUM 8573C -- a
# subset of the prior campaign's 4-model observation, still clearing the 3-model coverage
# target). The Slave binding change exposing Pool's allocation getters, together with
# tests/perf/test_pool_alloc_perf.py and tests/perf/test_batcher_combine_perf.py, gave the six
# metrics named just above their first real population. All six now carry a computed
# `bit-identical` verdict, n=120 clean samples apiece, minimum equals maximum equals median with
# zero spread on every observed model: combiner_count, pool_alloc_peak_bytes,
# pool_alloc_total_bytes, pool_alloc_total_count, slave_byte_count, slave_frame_count. None is
# demoted; each stays at TIER_1 with COMPARISON_BIT_IDENTICAL, now confirmed rather than
# unproven. Zero demotions this round, and no bound tier changes, but the regenerated invariance
# section does not restate the earlier verdicts verbatim, so the reason is worth recording
# exactly. Of the 21 metrics the first binding-tier update already bound, the 7 bit-identical ones
# re-report `bit-identical`. The 14 demoted ones do not re-report `demoted-to-tier-2`: 13 report
# `not-applicable-non-tier-1-candidate`, because their own committed records already carry the
# post-demotion tier_candidate and so are no longer Tier 1 candidates for the section to evaluate,
# and bytes_on_wire_ratio alone is still re-evaluated and reconfirmed as
# `demoted-to-tier-2-within-run`. The whole regenerated section therefore reports 13
# `bit-identical` (those 7 plus the 6 named above), 1 `demoted-to-tier-2-within-run`, and 41
# `not-applicable-non-tier-1-candidate`. No entry's bound tier moves.
#
# THIRD POST-CAMPAIGN BINDING TIER UPDATE, citing the corrected regenerated
# "Cross-CPU-model invariance" section in docs/plans/perf-ci-hardening/CAMPAIGN-REPORT.md over the
# same unchanged 24-run perf-harness/campaign-v3 population. The comparison itself was corrected,
# not the population: the prior comparison pooled every benchmark's samples for a metric into one
# list before applying the exact minimum-equals-maximum bar, so a metric collected on several
# benchmarks with legitimately differing counts could never pass that bar however deterministic
# each individual benchmark's cell was. The comparison now groups by (benchmark, CPU model) and
# evaluates every invariant-direction metric regardless of the candidate tier its own committed
# records carry (the prior demotion had already stamped a Tier 2 candidate tier onto every one of
# these metrics' records, so gating eligibility on candidate tier would have made the pooling
# defect permanent against this population).
#
# Nine promotions, zero demotions this round. Every one of the nine metrics below is separately
# constant on every benchmark it was measured on (n=120 per cell, zero spread), even though the
# raw values differ across benchmarks -- exactly what the pooled comparison could never see:
# buffer_copy_bytes, buffer_copy_count, gil_acquire_count, gil_release_count, scoped_gil_count,
# transaction_create_count, transaction_lock_acquisitions, transaction_request_bytes,
# transaction_request_count. Each moves from TIER_2/COMPARISON_DISPERSION_BAND to
# TIER_1/COMPARISON_BIT_IDENTICAL. Five metrics remain correctly demoted, now with the
# disagreeing benchmark(s) named directly per (benchmark, CPU model) rather than left to a pooled
# figure: frame_create_count, frame_lock_acquisitions, io_bytes, and io_call_count each disagree
# on all four udp_packetizer_perf_* benchmarks while agreeing on fifo_perf and
# stream_bridge_perf; bytes_on_wire_ratio's demotion is unaffected by the grouping fix since it is
# decided by within-run nondeterminism before the per-benchmark comparison ever runs.
#
# Resulting registry-wide tier counts: 22 at TIER_1, 26 at TIER_2, 7 at TIER_3 (previously 13, 35,
# 7).
_METRIC_ENTRIES: tuple[tuple[str, dict[str, Any]], ...] = (
    # -- Tier 1: mutex acquisitions --------------------------------------------------------
    ("transaction_lock_acquisitions", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison; n=120 clean samples per (benchmark,
        # model) cell, minimum equals maximum on every one of its 7 transaction-path
        # benchmarks across all 3 observed CPU models, zero spread on every cell).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "mutex_acquisitions",
        "source": "rogue.PerfCounters.getTransactionLockCount",
        "benchmarks": TRANSACTION_BENCHMARKS,
    }),
    ("frame_lock_acquisitions", {
        # Binding tier: demoted-to-tier-2-within-run (CAMPAIGN-REPORT.md invariance section).
        # The corrected per-benchmark comparison reconfirms the demotion: constant on
        # fifo_perf and stream_bridge_perf but varying across all four
        # udp_packetizer_perf_* benchmarks, which disagree.
        "tier": TIER_2,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "mutex_acquisitions",
        "source": "rogue.PerfCounters.getFrameLockCount",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    # -- Tier 1: buffer copies --------------------------------------------------------------
    ("buffer_copy_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison; n=120 clean samples per cell,
        # minimum equals maximum on every one of its 6 stream-path benchmarks across all
        # 3 observed CPU models, zero spread on every cell).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "buffer_copies",
        "source": "rogue.PerfCounters.getBufferCopyCount",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("buffer_copy_bytes", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison; n=120 clean samples per cell,
        # minimum equals maximum on every one of its 6 stream-path benchmarks across all
        # 3 observed CPU models, zero spread on every cell).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "bytes",
        "family": "buffer_copies",
        "source": "rogue.PerfCounters.getBufferCopyBytes",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    # -- Tier 1: heap allocations -------------------------------------------------------------
    # Scoped to COVERAGE_BENCHMARKS (pool_alloc_perf), not STREAM_BENCHMARKS: this family is
    # now measured on the one benchmark that holds a Python-readable Pool reflecting its own
    # real allocations. None of fifo_perf, stream_bridge_perf, or the four
    # udp_packetizer_perf_* identities expose such an instance, since Fifo, TcpServer,
    # TcpClient, and Prbs do not.
    ("pool_alloc_total_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's Cross-CPU-model invariance section;
        # n=120 clean samples agreeing across all 3 observed CPU models, min=max=median=200,
        # spread 0).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "heap_allocations",
        "source": "rogue.interfaces.stream.Pool.getAllocTotalCount",
        "benchmarks": COVERAGE_BENCHMARKS,
    }),
    ("pool_alloc_total_bytes", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's Cross-CPU-model invariance section;
        # n=120 clean samples agreeing across all 3 observed CPU models, min=max=median=200000,
        # spread 0).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "bytes",
        "family": "heap_allocations",
        "source": "rogue.interfaces.stream.Pool.getAllocTotalBytes",
        "benchmarks": COVERAGE_BENCHMARKS,
    }),
    ("pool_alloc_peak_bytes", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's Cross-CPU-model invariance section;
        # n=120 clean samples agreeing across all 3 observed CPU models, min=max=median=1000,
        # spread 0).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "bytes",
        "family": "heap_allocations",
        "source": "rogue.interfaces.stream.Pool.getAllocPeakBytes",
        "benchmarks": COVERAGE_BENCHMARKS,
    }),
    # -- Tier 1: Frame/Buffer construction (frame_create_count also stands in for the "Buffer
    # construction count" half of this family: every Buffer this phase's reduced-size repeats
    # allocate is counted by pool_alloc_total_count above under heap_allocations, so no second
    # frame_buffer_construction row is needed to avoid double-registering one physical count
    # under two metric names) --------------------------------------------------------------
    ("frame_create_count", {
        # Binding tier: demoted-to-tier-2 (CAMPAIGN-REPORT.md invariance section). The
        # corrected per-benchmark comparison reconfirms the demotion: constant on
        # fifo_perf and stream_bridge_perf but varying across all four
        # udp_packetizer_perf_* benchmarks, which disagree.
        "tier": TIER_2,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "frame_buffer_construction",
        "source": "rogue.PerfCounters.getFrameCreateCount",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    # -- Tier 1: transaction construction (transaction path has no counters at all today; the
    # getters below land in a later change, named here verbatim so the registry and the
    # eventual C++ symbol are pinned to the same name) --------------------------------------
    ("transaction_create_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison; n=120 clean samples per cell,
        # minimum equals maximum on every one of its 7 transaction-path benchmarks across
        # all 3 observed CPU models, zero spread on every cell).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "transaction_construction",
        "source": "rogue.PerfCounters.getTransactionCreateCount",
        "benchmarks": TRANSACTION_BENCHMARKS,
    }),
    ("transaction_request_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison; n=120 clean samples per cell,
        # minimum equals maximum on every one of its 7 transaction-path benchmarks across
        # all 3 observed CPU models, zero spread on every cell).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "transaction_construction",
        "source": "rogue.PerfCounters.getTransactionRequestCount",
        "benchmarks": TRANSACTION_BENCHMARKS,
    }),
    ("transaction_request_bytes", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison; n=120 clean samples per cell,
        # minimum equals maximum on every one of its 7 transaction-path benchmarks across
        # all 3 observed CPU models, zero spread on every cell).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "bytes",
        "family": "transaction_construction",
        "source": "rogue.PerfCounters.getTransactionRequestBytes",
        "benchmarks": TRANSACTION_BENCHMARKS,
    }),
    # -- Tier 1: Python/C++ boundary crossings, both paths plus the GIL-contention benchmark
    # itself, whose entire point is crossing behaviour under contention -----------------------
    ("gil_release_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison; n=120 clean samples per cell,
        # minimum equals maximum on every one of its 14 benchmarks across all 3 observed
        # CPU models, zero spread on every cell). The prior demotion was an artifact of
        # the pooled comparison mixing benchmarks whose GIL-crossing counts legitimately
        # differ (e.g. localGetRate issues none, remoteSetRate issues 3000): each
        # benchmark's own cell was already constant.
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "python_cpp_crossings",
        "source": "rogue.PerfCounters.getGilReleaseCount",
        "benchmarks": ALL_BENCHMARKS,
    }),
    ("gil_acquire_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison) -- the same measured fact as
        # gil_release_count above: n=120 clean samples per cell, minimum equals maximum on
        # every one of its 14 benchmarks across all 3 observed CPU models, zero spread.
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "python_cpp_crossings",
        "source": "rogue.PerfCounters.getGilAcquireCount",
        "benchmarks": ALL_BENCHMARKS,
    }),
    ("scoped_gil_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's regenerated Cross-CPU-model
        # invariance section, per-benchmark comparison; n=120 clean samples per cell,
        # minimum equals maximum on every one of its 14 benchmarks across all 3 observed
        # CPU models, zero spread on every cell).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "python_cpp_crossings",
        "source": "rogue.PerfCounters.getScopedGilCount",
        "benchmarks": ALL_BENCHMARKS,
    }),
    # -- Tier 1: Rogue-issued I/O calls (Rogue's own send/recv/poll call sites, not
    # process syscalls; scoped to the stream path only, since the transaction path runs
    # entirely against rogue.interfaces.memory.Emulate and issues none) --------------------
    ("io_call_count", {
        # Binding tier: demoted-to-tier-2 (CAMPAIGN-REPORT.md invariance section). The
        # corrected per-benchmark comparison reconfirms the demotion: constant on
        # fifo_perf and stream_bridge_perf but varying across all four
        # udp_packetizer_perf_* benchmarks, which disagree.
        "tier": TIER_2,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "rogue_issued_io_calls",
        "source": "rogue.PerfCounters.getIoCallCount",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("io_bytes", {
        # Binding tier: demoted-to-tier-2 (CAMPAIGN-REPORT.md invariance section). The
        # corrected per-benchmark comparison reconfirms the demotion: constant on
        # fifo_perf and stream_bridge_perf but varying across all four
        # udp_packetizer_perf_* benchmarks, which disagree.
        "tier": TIER_2,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "bytes",
        "family": "rogue_issued_io_calls",
        "source": "rogue.PerfCounters.getIoBytes",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    # -- Tier 1: existing zero-source-change counters, already bound
    # to Python, no new C++ needed ----------------------------------------------------------
    ("prbs_rx_count", {
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "prbs_frame_accounting",
        "source": "rogue.utilities.Prbs.getRxCount",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("prbs_tx_count", {
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "prbs_frame_accounting",
        "source": "rogue.utilities.Prbs.getTxCount",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("prbs_rx_bytes", {
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "bytes",
        "family": "prbs_frame_accounting",
        "source": "rogue.utilities.Prbs.getRxBytes",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("prbs_tx_bytes", {
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "bytes",
        "family": "prbs_frame_accounting",
        "source": "rogue.utilities.Prbs.getTxBytes",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("prbs_rx_errors", {
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "prbs_frame_accounting",
        "source": "rogue.utilities.Prbs.getRxErrors",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("prbs_tx_errors", {
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "prbs_frame_accounting",
        "source": "rogue.utilities.Prbs.getTxErrors",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    # Scoped to COVERAGE_BENCHMARKS (pool_alloc_perf), not STREAM_BENCHMARKS: this family is
    # measured on the coverage benchmark's bare terminal Slave, whose base acceptFrame
    # implementation runs and therefore counts. The four legacy stream identities are dropped
    # from the scope because the only Slave-family object those modules construct is a Prbs,
    # which re-implements the accept path in C++ and leaves these two getters at a permanent
    # zero.
    ("slave_frame_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's Cross-CPU-model invariance section;
        # n=120 clean samples agreeing across all 3 observed CPU models, min=max=median=200,
        # spread 0).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "slave_frame_accounting",
        "source": "rogue.interfaces.stream.Slave.getFrameCount",
        "benchmarks": ("pool_alloc_perf",),
    }),
    ("slave_byte_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's Cross-CPU-model invariance section;
        # n=120 clean samples agreeing across all 3 observed CPU models, min=max=median=200000,
        # spread 0).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "bytes",
        "family": "slave_frame_accounting",
        "source": "rogue.interfaces.stream.Slave.getByteCount",
        "benchmarks": ("pool_alloc_perf",),
    }),
    # Scoped to COVERAGE_BENCHMARKS (batcher_combine_perf), not STREAM_BENCHMARKS: the metric
    # is the combiner's live queue depth (queue_.size()), not a cumulative counter, so its
    # per-repeat delta is the number of frames accepted into a batch during that repeat, which
    # holds only because the benchmark drains the queue with sendBatch() after the final
    # snapshot rather than inside the measured region. The four legacy stream identities are
    # dropped from the scope because none of the pre-existing modules constructs a combiner.
    ("combiner_count", {
        # Binding tier: bit-identical (CAMPAIGN-REPORT.md's Cross-CPU-model invariance section;
        # n=120 clean samples agreeing across all 3 observed CPU models, min=max=median=200,
        # spread 0).
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "batcher_combining",
        "source": "rogue.protocols.batcher.CombinerV1.getCount / rogue.protocols.batcher.CombinerV2.getCount",
        "benchmarks": ("batcher_combine_perf",),
    }),
    ("core_drop_count", {
        "tier": TIER_1,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_BIT_IDENTICAL,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "count",
        "family": "packetizer_drops",
        "source": "rogue.protocols.packetizer.Core.getDropCount / rogue.protocols.packetizer.CoreV2.getDropCount",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    # -- Tier 1: bytes-on-wire per payload byte, derived, stream path only (UNCOVERED_FAMILIES
    # above records the transaction-path gap) ------------------------------------------------
    ("bytes_on_wire_ratio", {
        # Binding tier: demoted-to-tier-2-within-run (CAMPAIGN-REPORT.md invariance section) --
        # inherits io_bytes' own within-run nondeterminism, since it is derived from io_bytes.
        # Reconfirmed, unchanged, by the corrected per-benchmark comparison: a within-run
        # demotion is decided before the per-benchmark comparison ever runs, so the grouping
        # correction that promoted the nine metrics above and reconfirmed the four
        # cross-model demotions has nothing to say about this one.
        "tier": TIER_2,
        "direction": DIRECTION_INVARIANT,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "ratio",
        "family": "bytes_on_wire",
        "source": "rogue.PerfCounters.getIoBytes / rogue.utilities.Prbs.getTxBytes",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    # -- Tier 2: dual-clock CPU time per unit work (both process and thread clocks, each
    # divided by bytes and by operations) ----------------------------------------------------
    ("cpu_process_ns_per_byte", {
        "tier": TIER_2,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "ns/byte",
        "family": "cpu_time_per_unit_work",
        "source": "resource.getrusage(RUSAGE_SELF).ru_utime + ru_stime, divided by bytes",
        "benchmarks": ALL_BENCHMARKS,
    }),
    ("cpu_process_ns_per_op", {
        "tier": TIER_2,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "ns/op",
        "family": "cpu_time_per_unit_work",
        "source": "resource.getrusage(RUSAGE_SELF).ru_utime + ru_stime, divided by operations",
        "benchmarks": ALL_BENCHMARKS,
    }),
    ("cpu_thread_ns_per_byte", {
        "tier": TIER_2,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "ns/byte",
        "family": "cpu_time_per_unit_work",
        "source": "time.clock_gettime(CLOCK_THREAD_CPUTIME_ID), divided by bytes",
        "benchmarks": ALL_BENCHMARKS,
    }),
    ("cpu_thread_ns_per_op", {
        "tier": TIER_2,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "ns/op",
        "family": "cpu_time_per_unit_work",
        "source": "time.clock_gettime(CLOCK_THREAD_CPUTIME_ID), divided by operations",
        "benchmarks": ALL_BENCHMARKS,
    }),
    # -- Tier 2: slowdown_ratio, self-normalizing (deferred from Phase 1's initial metric set) --
    ("slowdown_ratio", {
        "tier": TIER_2,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "ratio",
        "family": "gil_contention_slowdown",
        "source": "tests/perf/test_block_gil_contention_perf.py: contended_s / baseline_s",
        "benchmarks": GIL_BENCHMARKS,
    }),
    # -- Tier 3: existing published wall-clock fields, non-gating (unchanged meaning) --
    ("avg_ns", {
        "tier": TIER_3,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_NON_GATING,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "ns/op",
        "family": "wall_clock_timing",
        "source": "tests/perf/test_variable_rate_perf.py: _measure_operation",
        "benchmarks": TRANSACTION_BENCHMARKS,
    }),
    ("rate_hz", {
        "tier": TIER_3,
        "direction": DIRECTION_HIGHER_IS_BETTER,
        "comparison": COMPARISON_NON_GATING,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "ops/s",
        "family": "wall_clock_timing",
        "source": "tests/perf/test_variable_rate_perf.py: _measure_operation",
        "benchmarks": TRANSACTION_BENCHMARKS,
    }),
    ("cycles", {
        "tier": TIER_3,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_NON_GATING,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "cycles",
        "family": "wall_clock_timing",
        "source": "tests/perf/test_variable_rate_perf.py: hwcounter sample around _measure_operation",
        "benchmarks": TRANSACTION_BENCHMARKS,
    }),
    ("throughput_mb_s", {
        "tier": TIER_3,
        "direction": DIRECTION_HIGHER_IS_BETTER,
        "comparison": COMPARISON_NON_GATING,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "MB/s",
        "family": "wall_clock_timing",
        "source": "tests/perf/: (received * frame_size) / elapsed",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("elapsed_sec", {
        "tier": TIER_3,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_NON_GATING,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "s",
        "family": "wall_clock_timing",
        "source": "tests/perf/: a monotonic wall-clock timer around the generate-and-drain loop",
        "benchmarks": STREAM_BENCHMARKS,
    }),
    ("baseline_s", {
        "tier": TIER_3,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_NON_GATING,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "s",
        "family": "wall_clock_timing",
        "source": "tests/perf/test_block_gil_contention_perf.py: _drain with no contender",
        "benchmarks": GIL_BENCHMARKS,
    }),
    ("contended_s", {
        "tier": TIER_3,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_NON_GATING,
        "calibration_pairing": CALIBRATION_NONE,
        "unit": "s",
        "family": "wall_clock_timing",
        "source": "tests/perf/test_block_gil_contention_perf.py: _drain with a GIL contender",
        "benchmarks": GIL_BENCHMARKS,
    }),
) + tuple(
    # -- Tier 2: calibration-normalized ratios, one per Tier 2 CPU candidate metric and per
    # calibration component. Every pairing is computed and kept; the campaign report decides
    # which one, if any, measurably flattens across-host dispersion without inflating
    # within-host dispersion. calibration_pairing names the component itself, rather than a
    # decision made here. --------------------------------------------------
    (f"{base}_over_{component}", {
        "tier": TIER_2,
        "direction": DIRECTION_LOWER_IS_BETTER,
        "comparison": COMPARISON_DISPERSION_BAND,
        "calibration_pairing": component,
        "unit": "dimensionless_ratio",
        "family": "cpu_time_per_unit_work_normalized",
        "source": f"{base}, divided by env_fingerprint.collect_calibration_vector().components.{component}.median",
        "benchmarks": ALL_BENCHMARKS,
    })
    for base in ("cpu_process_ns_per_byte", "cpu_process_ns_per_op", "cpu_thread_ns_per_byte", "cpu_thread_ns_per_op")
    for component in CALIBRATION_COMPONENTS
)


def validate_registry(
    entries: tuple[tuple[str, dict[str, Any]], ...] = _METRIC_ENTRIES,
) -> dict[str, dict[str, Any]]:
    """Validate `entries` and return the deduplicated metric-name to
    descriptor mapping. Raises RegistryError on a duplicate metric name (so
    the later definition can never silently win), a missing required key, an
    unrecognized tier/direction/comparison/calibration-pairing value, a Tier
    1 `source` naming a getter outside KNOWN_TIER_1_SOURCES, or a
    REQUIRED_METRIC_FAMILIES entry absent from both the registry and
    UNCOVERED_FAMILIES.
    """
    metrics: dict[str, dict[str, Any]] = {}
    for name, descriptor in entries:
        if name in metrics:
            raise RegistryError(f"duplicate metric name: {name!r}")
        missing = [key for key in _REQUIRED_KEYS if key not in descriptor]
        if missing:
            raise RegistryError(f"metric {name!r} is missing required keys: {sorted(missing)}")
        if descriptor["tier"] not in _VALID_TIERS:
            raise RegistryError(f"metric {name!r} has unknown tier: {descriptor['tier']!r}")
        if descriptor["direction"] not in _VALID_DIRECTIONS:
            raise RegistryError(f"metric {name!r} has unknown direction: {descriptor['direction']!r}")
        if descriptor["comparison"] not in _VALID_COMPARISONS:
            raise RegistryError(f"metric {name!r} has unknown comparison: {descriptor['comparison']!r}")
        if descriptor["calibration_pairing"] not in _VALID_CALIBRATION_PAIRINGS:
            raise RegistryError(
                f"metric {name!r} has unknown calibration_pairing: {descriptor['calibration_pairing']!r}"
            )
        if descriptor["tier"] == TIER_1:
            for token in _tier1_source_tokens(descriptor["source"]):
                if token not in KNOWN_TIER_1_SOURCES:
                    raise RegistryError(
                        f"metric {name!r} has a Tier 1 source naming an unrecognized getter: {token!r}"
                    )
        metrics[name] = descriptor

    covered_families = {descriptor["family"] for descriptor in metrics.values()}
    for family in REQUIRED_METRIC_FAMILIES:
        if family not in covered_families and family not in UNCOVERED_FAMILIES:
            raise RegistryError(
                f"required metric family {family!r} is neither registered by any metric nor "
                "recorded in UNCOVERED_FAMILIES"
            )

    return metrics


# Validated at import time so a duplicate metric name, an unknown tier value, an unknown
# direction, an unknown comparison, an unknown calibration pairing, a missing required key, an
# unrecognized Tier 1 source, or an uncovered required metric family raises here rather than
# resolving to a later definition silently winning.
METRICS: dict[str, dict[str, Any]] = validate_registry()


def metric_descriptor(name: str) -> dict[str, Any]:
    if name not in METRICS:
        raise RegistryError(f"unknown metric: {name!r}")
    return METRICS[name]


def tier_for(name: str) -> str:
    return metric_descriptor(name)["tier"]


def metrics_for_benchmark(benchmark: str) -> tuple[str, ...]:
    return tuple(
        name for name in sorted(METRICS)
        if benchmark in METRICS[name]["benchmarks"]
    )
