# Threshold Assertion Dispositions

This file records the disposition of both existing wall-clock threshold assertions in
`tests/perf/`, with every evidence figure recomputed from the published `gh-pages` history at
authoring time. No file under `tests/perf/` is modified by this work; both dispositions are
written decisions only.

Every recomputed figure below is quoted in `f"{value:.6g}"` form, matching the float format
the generated noise floor sidecar uses, so a later comparison can check the two by exact
string match. Figures are recomputed with a list-argument `subprocess.run` over
`git ls-tree`/`git show` against `origin/gh-pages`, `check=True`, no shell, so a failed git
call aborts the recomputation rather than silently yielding a zero-sample figure. The
population is the 45 `perf/branches/*/history/<sha>.json` records; `latest.json`,
`index.json`, and `index.html` files under `perf/` are excluded as duplicates or indices, not
independent measurements.

## Disposition 1: `test_variable_rate_perf.py` cycles check, demoted to informational

### Which comparison is live on CI

`pip_requirements.txt:30` and `pip_requirements_ci.txt:22` both carry `hwcounter` under a
`platform_system == "Linux" and platform_machine == "x86_64"` marker. The perf job in
`.github/workflows/rogue_ci.yml` runs on `ubuntu-24.04` (Linux x86_64), so `hwcounter` imports
successfully there, `HAS_HWCOUNTER` is `True`, and the live gating comparison is the cycles
branch at `tests/perf/test_variable_rate_perf.py:188`
(`result['cycles'] > MaxCycles[name]`). The nanoseconds-per-operation comparison at line 193
is reachable only in the `elif` taken when `HAS_HWCOUNTER` is `False`, which does not happen
on this runner. Collection of `cycles`, `avg_ns`, and `rate_hz` continues unchanged for the
published series; this disposition addresses only how the cycles figure is treated by a
future gate, not whether it is collected.

### Recomputed: non-null cycles coverage

Across all seven `variable_rate_perf_*` series, 315 of 315 published samples (45 records
times 7 operations) carry a non-null `cycles` field. `hwcounter` has never been unavailable
across the recorded history.

### Recomputed: three discrete implied clock rates

The implied clock rate for one sample is `cycles / (avg_ns * BENCH_COUNT * 1e-9)`, where
`BENCH_COUNT = 100000` from `tests/perf/test_variable_rate_perf.py:45` and `cycles` is the raw
whole-loop total while `avg_ns` is per-operation, so the `BENCH_COUNT` factor is required to
put the two on the same basis. Computed per record using the `remoteSetRate` series as a
representative (all seven operations within one record share the same host and therefore the
same implied rate, confirmed by clustering the full 315-sample population and finding the
same three clusters at 7x the per-record counts), the population splits into exactly three
discrete rates with no intermediate values:

| Implied rate | Records |
|---|---|
| 2.44542 GHz | 28 |
| 2.59613 GHz | 9 |
| 2.79346 GHz | 8 |

28 + 9 + 8 = 45, the full record population. These are unlabeled host groups reported by rate
and sample count only; no CPU family or vendor is named, since that would be inference from
external fleet documentation rather than measurement from this data.

### Recomputed: cycles CV against avg_ns CV per series

The coefficient of variation (sample stdev over mean, as a percent) of `cycles` tracks the
coefficient of variation of `avg_ns` closely for every one of the seven series, which is the
evidence that the cycles metric is wall clock in disguise rather than a hardware-invariant
proxy:

| Series | n | cycles CV % | avg_ns CV % |
|---|---|---|---|
| `linkedGetRate` | 45 | 5.21567 | 4.9037 |
| `linkedSetRate` | 45 | 6.04682 | 6.40743 |
| `localGetRate` | 45 | 5.48723 | 5.18345 |
| `localSetRate` | 45 | 6.42684 | 6.31784 |
| `remoteGetRate` | 45 | 5.89873 | 5.13549 |
| `remoteSetNvRate` | 45 | 7.13939 | 7.31501 |
| `remoteSetRate` | 45 | 6.56866 | 6.82646 |

If `cycles` carried genuine immunity to host frequency or steal time, its dispersion would be
markedly lower than `avg_ns`'s. It is not: the two move together within roughly one
percentage point on every series.

### Recomputed: per-series headroom against `MaxCycles`

`MaxCycles` is the ceiling table at `tests/perf/test_variable_rate_perf.py:37-43`. Headroom is
the ceiling divided by the observed maximum `cycles` across all 45 samples per series:

| Series | n | max cycles | `MaxCycles` limit | headroom |
|---|---|---|---|---|
| `remoteSetRate` | 45 | 3.25804e+09 | 8e+09 | 2.45547x |
| `remoteSetNvRate` | 45 | 2.73734e+09 | 7e+09 | 2.55723x |
| `linkedSetRate` | 45 | 3.41631e+09 | 9e+09 | 2.63442x |
| `remoteGetRate` | 45 | 2.0394e+09 | 6e+09 | 2.94204x |
| `linkedGetRate` | 45 | 2.2097e+09 | 8e+09 | 3.6204x |
| `localSetRate` | 45 | 7.96579e+08 | 8e+09 | 10.0429x |
| `localGetRate` | 45 | 5.3559e+08 | 6e+09 | 11.2026x |

The observed headroom ranges from 2.45547x (`remoteSetRate`, lowest) to 11.2026x
(`localGetRate`, highest), each over the full 45-sample population per series. `MaxCycles`
traces to no measured dispersion in the repository: it is described in the module's own
comment as "pre-existing tuned thresholds from the original x86/hwcounter-based test," and
`NOMINAL_CPU_HZ = 3.0e9` at `tests/perf/test_variable_rate_perf.py:46` (the constant used to
derive the fallback `MaxAvgNs` table) is the only stated basis for any of these numbers, not a
measured clock rate. Notably, none of the three recomputed implied clock rates above (2.44542,
2.59613, 2.79346 GHz) equals `NOMINAL_CPU_HZ`'s assumed 3.0 GHz; every host measured so far
runs slower than the assumption embedded in `MaxAvgNs`.

## Disposition 2: `test_block_gil_contention_perf.py` drain ceiling, retained

### Recomputed: headroom and sample count

`CEILING_S = 10.0` at `tests/perf/test_block_gil_contention_perf.py:44`. Across the 27
published records that contain the `block_gil_contention_drain` series, the observed maximum
`contended_s` is 0.123416, against the `ceiling_s` value of 10 carried in every one of those
27 records. That is a headroom of 81.0268x, and the assertion at
`tests/perf/test_block_gil_contention_perf.py:131` has never fired across this 27-record
population; the never-fired claim is bounded by that sample count and no larger.

### Reclassification: functional guard, not a performance threshold

`DRAIN_COUNT = 42000` at `tests/perf/test_block_gil_contention_perf.py:39` reproduces the
staged-update-queue drain from SLAC rogue issue #1262. That issue's pre-fix failure mode was a
42 to 126 second stall under GIL contention; this figure is sourced from the issue that
motivated the guard, not from the published perf population, and is explicitly marked here as
not recomputable from this data (there is no pre-fix record in the published history to
recompute it from). The recomputed 81.0268x headroom over an observed maximum of 0.123416 s
means the ceiling sits three orders of magnitude above anything the drain has actually taken:
catching a multi-second-to-multi-minute stall is a qualitatively different check than
detecting a percentage-scale regression, and a check with that much headroom cannot
false-positive on ordinary host noise. On that basis, `CEILING_S` is reclassified as a
functional regression guard for the #1262 stall rather than as a performance threshold subject
to the same treatment as the variable-rate cycles check above.

### Recomputed: median slowdown ratio

The published `slowdown_ratio` (`contended_s / baseline_s`) has a median of 1.91884 across the
27 records, ranging from 1.23478 to 2.18250. This is reported as characterization evidence,
not as a proposal to gate on it; `slowdown_ratio` is invisible to current comparison tooling
today because the series' `primary_metric` is null (`_metric_descriptor` in
`scripts/perf_data.py` recognizes only `avg_ns` and `throughput_mb_s`).

### Why the ceiling is not tightened

The ceiling is deliberately not tightened toward the recomputed measured dispersion above.
Tightening a 10.0 s ceiling toward, say, a small multiple of the observed 0.123416 s maximum
would convert a robust functional guard, which currently cannot false-positive on host noise,
into exactly the kind of noise-sensitive wall-clock threshold this project exists to remove.
The ceiling stays wide and stays a tripwire for the specific multi-second stall it was written
to catch.

## Scope of this record

Both dispositions above are written decisions only. No file under `tests/perf/` is modified
by this work: implementing the informational demotion of the variable-rate cycles check needs
a tier registry for an informational classification to land in, and that registry does not
exist yet; it is later harness and metric-registry work's responsibility to build it. Leaving
the `test_block_gil_contention_perf.py` assertion in place, unmodified, keeps a tripwire for
the #1262 stall in effect until a replacement gate exists to take over that role.

## Hand-off requirement: implied clock rate in the environment fingerprint

The three unlabeled host groups recomputed above (28 records at 2.44542 GHz, 9 records at
2.59613 GHz, 8 records at 2.79346 GHz) are reported by rate and sample count only; no CPU
vendor, family, or SKU is named, because attributing a rate to a named CPU family from
external fleet documentation would be inference, not measurement, from the data analyzed
here. The runner capability probe work that follows this analysis must capture the implied
clock rate alongside the CPU model in its per-run environment fingerprint. Doing so
retroactively labels these three historical host groups with a real CPU identity and makes
the entire existing 45-record published series host-attributable going forward, which nothing
in the currently published record schema (`schema_version`, `ref_name`, `ref_slug`, `sha`,
`short_sha`, `run_id`, `run_url`, `published_at`, `benchmarks`) supports today.

## Finding: no back-fill of run metadata from the CI provider API

No back-fill of host or run metadata from the CI provider's API was attempted for this work,
and this is recorded as a finding rather than as an untried option. Three reasons: hosted
runner names are generic (they do not encode CPU model), the oldest published records in this
population predate the provider's log retention window, and the `gh` CLI available in this
environment is version 2.4.0 (March 2022), old enough that its API surface for querying
historical run metadata should be smoke-tested, not assumed, before any later work depends on
it.
