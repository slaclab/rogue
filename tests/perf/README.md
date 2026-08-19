# Performance Tests and the Perf Gate

This directory holds Rogue's performance test suite: register and memory
transaction throughput, and streaming frame and byte throughput through
`rogue::interfaces::stream`. A subset of the metrics these tests collect
also gate every pull request through the perf gate workflow, which compares
a candidate build against the pull request's own merge base, both built and
measured in the same job.

## Your perf check went red: start here

- The check you are looking at is the perf gate step of the CI workflow. It
  measures your branch and compares it against the merge base, both built
  and measured in the same job, so host-to-host variation cancels out
  rather than landing on one side of the comparison.
- A red check usually means the gate produced a verdict of `FAIL`. Read
  "What PASS, FAIL, and INCONCLUSIVE mean" below for what that verdict
  means and what to do about it. A red check can also mean the workflow
  failed before any verdict existed at all, for example a trusted baseline
  that is present at the merge base but corrupt or unparseable: that is an
  upstream defect on the base branch, not something your own change
  introduced, and it calls for reporting it rather than for changing
  anything in your own pull request.
- The step summary itself lists every failing metric with its tier and the
  dispersion figures its threshold was derived from. Start with that table
  before reading further in this file.

## What PASS, FAIL, and INCONCLUSIVE mean

Every run of the gate emits exactly one of three verdicts: `PASS`, `FAIL`,
or `INCONCLUSIVE`.

**FAIL** means at least one gating metric changed between the merge base
and the candidate build, with no tolerance for a metric whose baseline rule
is exact equality. When a run has both an un-exempted failing gating cell
and a separate inconclusive gating cell, the verdict is `FAIL`, not
`INCONCLUSIVE`: a real, un-exempted regression takes precedence over
uncertainty elsewhere in the same run. A `FAIL` step summary lists every
failing gating cell, not only the first, each with its tier and its
dispersion figures (sample count, spread, coefficient of variation, and
minimum detectable effect), in sorted benchmark then metric order. The
correct response to a `FAIL` is to read the listed cells, understand which
change moved them, and either fix the regression or justify why it is
expected. A `FAIL` should not be treated as something to dispatch again in
hope of a different answer: the change that caused it is deterministic and
will not go away by itself.

**INCONCLUSIVE** means the gate could not measure at least one gating cell
well enough to compare it, and never means the check secretly passed. An
`INCONCLUSIVE` verdict never blocks a pull request. The step summary names
which of the following eleven enumerated conditions fired for each affected
cell:

- `insufficient-clean-samples`
- `guard-exceeded`
- `metric-absent-from-leg`
- `benchmark-errored`
- `merge-base-build-failed`
- `tree-hash-pair-mismatch`
- `secondary-window-flag`
- `within-run-nondeterminism`
- `no-gating-cell-evaluated`
- `baseline-cell-missing`
- `trusted-baseline-absent`

These eleven split exhaustively into two sets. The gate automatically
retries the measurement exactly once, and only when every inconclusive
cell's condition falls in the retry-eligible set below, because a
re-measurement can plausibly change a transient or contention-driven
outcome:

- `insufficient-clean-samples`
- `guard-exceeded`
- `secondary-window-flag`
- `within-run-nondeterminism`
- `benchmark-errored`
- `metric-absent-from-leg`

The remaining five are structural: a retry cannot change any of them,
because each describes the run itself or the baseline rather than one
measurement, so the gate does not spend its one retry on them:

- `tree-hash-pair-mismatch`
- `merge-base-build-failed`
- `baseline-cell-missing`
- `no-gating-cell-evaluated`
- `trusted-baseline-absent`

A run that evaluated zero gating cells resolves to a non-blocking
`INCONCLUSIVE` carrying the `no-gating-cell-evaluated` reason. This is a
different situation from a baseline sidecar that could not be read or
parsed at all: that failure produces no verdict artifact at all, and the
evaluator exits with status 2, because a baseline the gate cannot read says
nothing about whether the candidate regressed and must not be reported in
the vocabulary of a measurement outcome. It is a third, again distinct,
situation from a trusted baseline that simply does not exist yet at the
merge base at all, which carries its own `trusted-baseline-absent` reason
and is covered on its own terms in "The introducing pull request" below.
The correct response to `INCONCLUSIVE` is to read which condition fired and
act on that specific condition, not to re-run or re-dispatch the check
hoping it turns green.

### The introducing pull request

A pull request whose merge base predates the gate baseline file entirely
gets a non-blocking `INCONCLUSIVE` carrying the `trusted-baseline-absent`
reason, because there is nothing committed at the merge base to compare
against yet. This is expected, not a defect: it is the normal state for any
pull request whose base branch has never carried the baseline file, most
obviously the pull request that introduces the gate itself. It resolves
itself with no action needed once that pull request merges and the baseline
exists on the base branch, so every later pull request's own merge base
carries it. The paired measurement still runs in full on this outcome; only
the comparison against a baseline is impossible, not the measurement
itself.

This is a different fact from a trusted baseline that is present at the
merge base but corrupt, unparseable, or missing its `cells` mapping: that
case is an upstream defect on the base branch a human must fix, and it
keeps failing loudly with no verdict at all, exactly as an unreadable
`--record` does.

**PASS** means every gating cell's exact-equality comparison between the
candidate and the merge base came back unchanged, and nothing more. A
`PASS` does not prove the change introduced no performance regression: it
means the gating counters were unchanged against the merge base, while the
wall-clock metrics this suite also collects are recorded for humans reading
trends on the published history and never gate a run at all.

## Reproducing a gate result locally

Two layers of reproduction, each verified at the strongest level available. The first works
offline right now, from a clean shell, with no build and no environment activation. The second
names the real mechanism the gate itself runs, but its evidence is a real hosted run, not a
local run this documentation claims to have made.

### Layer one: re-score a collected record offline

`scripts/perf_gate_evaluator.py` imports only the Python standard library, so re-scoring a
collected two-leg record against the committed baseline needs no conda environment, no build,
and no network. Run it exactly as printed, from the repository root:

```sh
python3 scripts/perf_gate_evaluator.py \
  --record docs/plans/perf-ci-hardening/gate-runs/32200785019-ab-record.json \
  --baseline docs/plans/perf-ci-hardening/gate-baseline.json \
  --out-json /tmp/gate-check.json \
  --out-md /tmp/gate-check.md
```

This exits `0`, and `/tmp/gate-check.md` begins:

```
Verdict: FAIL
Gating cells evaluated: 128
```

`--record` and `--baseline` are the two required inputs; `--out-json` and `--out-md` are
optional and only control where the rendered evaluation is written. Two exit behaviors are
worth knowing before running this against a different record: `--exit-nonzero-on-fail` makes a
`FAIL` verdict exit `1`, and never makes an `INCONCLUSIVE` verdict do so. An unreadable or
unparseable `--baseline` is a different failure entirely: the evaluator prints why it could not
be read and exits `2`, writing no verdict artifact at all, because a baseline it cannot read
says nothing about whether the candidate regressed.

Every reproduce command a generated report prints for itself is byte-identical to the command
that produced it, and those commands read measurement populations that are not carried in this
repository. Before running one of those, fetch the annotated tag
`perf-ci-hardening-evidence-v1` recorded in
`docs/plans/perf-ci-hardening/gate-runs/evidence-tag.json`, then run the unchanged command from
that checkout; the sidecar carries the tag's resolved commit, so it is not repeated here.

### Layer two: reproduce the whole paired measurement

The mechanism the gate itself runs on every pull request is two `git worktree` checkouts
sharing one job's own object store and one shared compiler cache: one worktree for the pull
request's head commit, one for its resolved merge base, with interleaved measurement rounds run
through the same measurement implementation on both. `scripts/perf_gate_ab_runner.py` drives
this, and enforces a floor of `180` seconds on each round's own share of the remaining time
budget for one leg, so a round is skipped outright rather than started with a share too small
to use.

This layer's evidence is a real hosted gate run, not a local run this documentation claims to
have made. `.github/workflows/perf_gate.yml` invokes it as:

```sh
python scripts/perf_gate_ab_runner.py \
  --out gate-results/ab-record.json \
  --candidate-ref <the pull request's own head commit sha> \
  --merge-base-ref <the resolved merge base sha> \
  --mode null \
  --label perf-gate \
  --rounds 2 \
  --worktree-root <a job-scoped temporary directory> \
  --baseline <the trusted baseline extracted at the merge base sha> \
  --merge-base-source <how the merge base was resolved> \
  --deadline-seconds 1260 \
  --round-share-floor-seconds 180 \
  --hang-diagnostics-dir gate-results/hang-diagnostics \
  --hang-diagnostics-lead-seconds 60 \
  --print-summary > gate-results/ab-summary.md
```

Local collection of the performance test modules under `tests/perf/` is blocked on the
authoring machine by a stray system-wide `tests` package that shadows this repository's own
`tests/` namespace package, which is an environment defect outside this repository rather than
a defect in this procedure. The symptom to recognize: `pytest` fails at collection with
`ModuleNotFoundError: No module named 'tests.perf'` while importing a `tests/perf/test_*.py`
module. The working local invocation that does exist, and that this repository's own tests
under `tests/utilities/` already rely on, is sourcing the built runtime tree in the same shell
before calling `pytest`:

```sh
bash -c 'source build/setup_rogue.sh; python -m pytest tests/utilities -q'
```

That is what actually runs locally today; it does not collect `tests/perf/` itself, for the
reason just stated.

## When the change is intentional

The gate's exact-equality comparison asks one question: did this pull request's own measured
counter differ from its merge base's own measured counter, both built and measured in the same
job. It does not ask whether the counter got worse. An optimization that removes an allocation,
a copy, or a lock acquisition changes that counter exactly as much as a regression that adds
one, so it fails the gate exactly as a regression would. This is the gate working as designed,
not the gate being wrong.

### Why this is not a workaround

The comparison is always candidate against merge base, measured together in the same job; the
committed baseline sidecar is never the comparand (see "What PASS, FAIL, and INCONCLUSIVE
mean" above). So the failure this section is about is one time: once the intentional change
merges, every later pull request's own merge base already carries it, and the comparison is
clean again with nothing to regenerate. The affected cell may afterward fall outside its
recorded minimum-to-maximum band and raise an informational drift note on an otherwise clean
`PASS`, which is a note, not a gate. Do not reapply the procedure below on a later pull request
for the same already merged change; there is nothing left for it to exempt.

### The procedure

Add a `Perf-Gate-Override` trailer to the pull request's head commit message. It is read from
that head commit only: a trailer on an earlier commit of the same branch has no effect, and
pushing a new commit re-runs the gate and re-reads the trailer from the new head.

Grammar: a comma-separated list of `benchmark.metric` cell tokens, then a semicolon, then a
justification. The benchmark component accepts upper and lower case letters, digits, and
underscores, because the transaction benchmark identities (for example `linkedGetRate`) are
camelCase; the metric component accepts only lowercase letters, digits, and underscores.
Neither component can contain a dot, a path separator, a shell metacharacter, a leading dash,
or a wildcard: nothing but a well-formed cell name can survive the pattern.

The justification has a minimum length of `20` Unicode code points, counted on the
whitespace-stripped value, not bytes: a value of exactly `20` code points is accepted, and one
fewer is rejected with `justification-below-minimum-length`.

A trailer is rejected for exactly one of five reasons, each named in the recorded override
section:

- `no-semicolon-separator`: the value carries no semicolon at all.
- `empty-justification`: the text after the semicolon is empty once stripped.
- `justification-below-minimum-length`: the justification is under `20` code points.
- `empty-cell-list`: the text before the semicolon named no cell at all.
- `malformed-cell-token`: a named cell does not match the `benchmark.metric` pattern.

A rejected trailer exempts nothing at all, and the step summary now says so explicitly: status,
rejection reason, author, and the trailer as written.

An accepted trailer's named cells that do not land where expected are recorded with exactly one
of three reasons, never silently dropped:

- `gating-but-not-failing`: the cell gates, but was not failing in this run.
- `present-but-not-gating`: the cell exists in the baseline, but its own rule is not
  exact-equality, so it never gates at all.
- `absent-from-baseline`: no cell by that name exists in the committed baseline.

### What is not a remedy

Three things are not a remedy for a genuine, unintended regression, and none of them is a
substitute for fixing it:

- The escape hatch itself. It exists for a change the author intends, not for a change nobody
  has looked at yet.
- `ROGUE_PERF_GATE_REPORT_ONLY`, the repository variable `.github/workflows/perf_gate.yml`
  reads to decide whether the gate blocks. Its polarity is inverted from the usual convention:
  absent means blocking. It is a maintainer level kill switch for the whole gate, not a
  per-pull-request remedy for one failing check.
- Editing the committed baseline sidecar. It has no effect on this comparison at all, because
  the baseline is never the comparand (see "Why this is not a workaround" above).

The documented response to an unintended regression is to fix it.

## The metric tiers

Every metric `tests/perf/` collects belongs to one of three tiers, and the tier decides
whether the metric may ever gate a pull request.

- **Tier 1, deterministic counts of work performed.** Buffer copies, heap allocations,
  frame and buffer constructions, mutex acquisitions, boundary crossings between Python
  and native code, and bytes on the wire per payload byte. Only this tier may gate by
  default.
- **Tier 2, normalized costs.** Processor time per unit of work, and a
  calibration-normalized ratio. This tier may gate only where measured dispersion
  supports it, and as of this baseline no Tier 2 cell does.
- **Tier 3, wall-clock rates.** Megabytes per second, transactions per second, frames per
  second, and nanoseconds per operation. This tier never gates. The next section argues
  why.

A metric is not admitted to the gating tier merely by declaring a tier in the registry.
It is admitted only if it is proven bit identical across the processor models actually
observed in the measurement campaign; a candidate that fails that test is recorded as
demoted to the normalized tier rather than quietly kept at Tier 1. The registry binds 22
metrics to the gating tier by this rule, and the committed baseline resolves that into
128 gating cells across the benchmarks that exercise them.

The decision itself, once a cell gates, is exact equality. `scripts/perf_gate_evaluator.py`
computes `delta = candidate_value - base_value` and returns
`VERDICT_PASS if delta == 0 else VERDICT_FAIL`. There is no tolerance band anywhere in
that comparison. The recorded dispersion (a gating cell's own observed minimum and
maximum) is used for two different things instead: deciding which cells are eligible to
gate in the first place, and raising an informational drift note on an otherwise-passing
cell whose candidate value falls outside its own recorded minimum-to-maximum band. The
percentage delta a report prints for a failing cell is informational in the same sense:
it helps a reader gauge the size of a regression, and plays no part in the verdict.

The committed baseline carries far more cells than gate. It holds 525 total cells, of
which 128 gate and 22 are the distinct metrics those gating cells belong to. Of the 525,
223 carry at least one measured sample at a minimum of 5 clean samples (observed between
94 and 120 samples on the measured cells), and 302 carry no sample at all. A metric with
no gating cell in this baseline never gates, whatever tier the registry assigns it, and a
cell whose sample count falls below the recorded minimum has its statistic suppressed
rather than reported.

The measurement discipline behind every cell, from `tests/perf/_perf_harness.py`: five
clean samples are required before a benchmark's statistic is reported
(`DEFAULT_TARGET_CLEAN_SAMPLES = 5`); a 15 second per-benchmark guard produces an
inconclusive result rather than a value if it fires
(`DEFAULT_BENCHMARK_GUARD_SECONDS = 15.0`); and a sample is rejected as contaminated,
rather than averaged in, when it falls outside a robust band of the median plus or minus
3.0 times 1.4826 times the median absolute deviation (`DEFAULT_MAD_SIGMA_MULTIPLIER` and
`MAD_SIGMA_SCALE`).

## Why wall-clock throughput is never gated

The case against gating a wall-clock number rests on three legs, each a number measured
in this repository, each naming the committed artifact that carries it. None of the three
argues from principle or from anything outside this repository.

**Leg one: the measured dispersion of the published wall-clock metrics over the published
history.** `docs/plans/perf-ci-hardening/noise-floor.json` computes these figures over 45
published `gh-pages` history records, rendered in
`docs/plans/perf-ci-hardening/NOISE-FLOOR-REPORT.md`. Over that history,
`fifo_perf.throughput_mb_s` carries a coefficient of variation of 14.85% (n=44),
`stream_bridge_perf.throughput_mb_s` carries 15.07% (n=45), and the transaction path's
own rate and latency figures carry a similar spread:
`variable_rate_perf_linkedGetRate.avg_ns` at 4.90% and its paired `.rate_hz` at 4.78%
(both n=45). A deterministic count collected over the same history sits at exactly 0%:
`fifo_perf.frames_sent`, `frames_received`, and `frame_size` each report a median absolute
deviation of 0 and a coefficient of variation of 0 across the same 44 to 45 records. A
run-to-run spread of one to two tens of a percent on the wall-clock side, against exactly
zero on the deterministic side, is large enough that any fixed percentage threshold on
the wall-clock figure either fires on ordinary noise or is set so wide it catches nothing.

**Leg two: the contrast measured in the same campaign.** This is not an argument that
timing does not matter; it is a measurement showing that on this runner fleet the
deterministic counts carry signal and the timings carry the host.
`docs/plans/perf-ci-hardening/CAMPAIGN-REPORT.md` records that every metric this registry
binds to the gating tier -- `buffer_copy_bytes`, `buffer_copy_count`, `combiner_count`,
`core_drop_count`, the `pool_alloc_*` and `prbs_*` families, the `transaction_*` family,
and the `gil_acquire_count` / `gil_release_count` / `scoped_gil_count` family -- reported
`bit-identical` across every one of the 3 processor models this campaign observed (AMD
EPYC 7763 64-Core Processor, AMD EPYC 9V74 80-Core Processor, and INTEL(R) XEON(R)
PLATINUM 8573C). Over the same 3 processor models and the same clean campaign runs, every
wall-clock and dual-clock CPU-time metric -- `avg_ns`, `throughput_mb_s`, `rate_hz`,
`elapsed_sec`, and the `cpu_process_ns_per_*` / `cpu_thread_ns_per_*` family -- is recorded
`not-applicable-non-invariant-metric`: its own registry direction is not invariant, so the
campaign never even compares it for cross-model agreement, because doing so would answer a
question the metric was never meant to answer.

**Leg three: this repository's own existing instance of the failure mode.** This is why
the argument is made here rather than borrowed from outside: this repository already
carries the mistake leg one and leg two argue against. `NOMINAL_CPU_HZ = 3.0e9` in
`tests/perf/test_variable_rate_perf.py` converts a measured cycle count into a
wall-clock-derived threshold, `MaxAvgNs`, by dividing a hardcoded cycle budget by an
assumed 3.0 GHz processor frequency, on the same runner fleet this campaign just measured
running 3 different processor models. That single constant mixes work done with host
speed inside one hardcoded number, on a fleet where the host speed is not one number.

**The price.** The tier ladder deliberately cannot see a regression that changes timing
without changing any deterministic count, and the validation campaign's own
`per-transaction-delay` seeded regression is exactly that: `docs/plans/perf-ci-hardening/GATE-VALIDATION-REPORT.md`
records that "no gating metric observes this regression: elapsed time is exactly what the
tier ladder deliberately refuses to gate," and that it is expected to surface only in the
wall-clock and dual-clock CPU-time figures, never as a gate detection. Even that
non-gating visibility is inconsistent: across the runs that seeded this regression, the
non-gating dispersion check flagged it at one injected magnitude (10000, detected on 6 of
6 runs) and missed it at three others (1000, 100000, and 1000000, each detected on 0 of 1
run). This is a designed blind spot with a named cost, not an oversight, and a maintainer
should not read a `PASS` as ruling out every performance regression. Closing this gap
would require a gating rule over a timing metric, which is exactly what this design rules
out.

**What the wall-clock tier is still for.** It is still collected, still published, and its
meaning is unchanged: a human reading trends on the published `gh-pages` history keeps
everything they had before this gate existed. The one maintainer-level control over
whether the gate blocks at all is the repository variable
`ROGUE_PERF_GATE_REPORT_ONLY`, and its polarity is inverted from the usual convention:
absent means blocking.

## The perf modules and their benchmarks

`tests/perf/` has seven modules, and each publishes one or more benchmark identities. This
list exists because a failing cell is reported as a benchmark name joined to a metric
name, and this is how a reader gets from that failing cell to the file that produced it.
The mapping below is validated at import time against the registry's own complete
benchmark set (`scripts/perf_gate_ab_runner.py`'s `_validate_module_benchmarks`), so a
benchmark missing from this list would fail that import rather than be silently absent
from it. For what each module actually measures versus what its name suggests, see
`docs/plans/perf-ci-hardening/MODULE-AUDIT.md` rather than a duplicate of that audit here.

| Module | Benchmarks |
|---|---|
| `tests/perf/test_variable_rate_perf.py` | `linkedGetRate`, `linkedSetRate`, `localGetRate`, `localSetRate`, `remoteGetRate`, `remoteSetNvRate`, `remoteSetRate` |
| `tests/perf/test_fifo_perf.py` | `fifo_perf` |
| `tests/perf/test_stream_bridge_perf.py` | `stream_bridge_perf` |
| `tests/perf/test_udp_packetizer_perf.py` | `udp_packetizer_perf_v1_jumbo`, `udp_packetizer_perf_v1_std`, `udp_packetizer_perf_v2_jumbo`, `udp_packetizer_perf_v2_std` |
| `tests/perf/test_block_gil_contention_perf.py` | `block_gil_contention_drain` |
| `tests/perf/test_pool_alloc_perf.py` | `pool_alloc_perf` |
| `tests/perf/test_batcher_combine_perf.py` | `batcher_combine_perf` |

## Where the numbers come from

Every figure quoted anywhere in this document traces to one of these committed
artifacts:

- `docs/plans/perf-ci-hardening/gate-baseline.json` and its rendered companion
  `GATE-BASELINE.md`: the gating cell set and the per-cell derivations.
- `docs/plans/perf-ci-hardening/noise-floor.json` and its rendered companion
  `NOISE-FLOOR-REPORT.md`: the published wall-clock dispersion figures.
- `docs/plans/perf-ci-hardening/campaign-report.json` and its rendered companion
  `CAMPAIGN-REPORT.md`: the per-metric dispersion and the cross-processor-model
  invariance verdicts.
- `docs/plans/perf-ci-hardening/gate-validation-report.json` and its rendered companion
  `GATE-VALIDATION-REPORT.md`: the confusion matrix and the per-metric smallest detected
  magnitudes.
- The capability matrix: what the runner fleet actually allows to be measured at all.
- The completion record: the procedures run and the budget this effort accounted for.

The full raw measurement populations behind those reports are not carried in this
repository. They are retained on the annotated tag `perf-ci-hardening-evidence-v1`,
recorded in `docs/plans/perf-ci-hardening/gate-runs/evidence-tag.json`; that sidecar
carries the tag's own resolved commit. If the fork holding that tag disappears, the
reports above remain and stay readable, but the underlying per-run records they were
computed from cannot be re-examined or re-aggregated.
