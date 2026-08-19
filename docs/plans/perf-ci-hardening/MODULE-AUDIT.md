# Perf Test Module Audit

## Scope

This audit compares what each of the five `tests/perf/` modules is named and documented to
measure against what the code actually times, what unit it emits, and what it asserts. It is
a judgement call written by hand, not a generated report: `tests/METHODOLOGY.md` explicitly
forbids a source-audit test that reads production source and asserts on implementation text,
so this comparison lives here as prose instead.

Every field name below was confirmed by reading the `emit_perf_result` call site in each
module, not assumed from the module name. `emit_perf_result` in `tests/perf/_perf_metrics.py`
is the single emission point, so the full set of published fields per series is exactly the
set of keyword arguments passed at each of the five call sites.

## Series attribution

Series names are quoted byte for byte as published, with no case folding and no
normalization, so this table can be checked against the live published records by exact
string match.

| Module | Published series |
|---|---|
| `test_block_gil_contention_perf.py` | `block_gil_contention_drain` |
| `test_fifo_perf.py` | `fifo_perf` |
| `test_stream_bridge_perf.py` | `stream_bridge_perf` |
| `test_udp_packetizer_perf.py` | `udp_packetizer_perf_v1_jumbo` |
| `test_udp_packetizer_perf.py` | `udp_packetizer_perf_v1_std` |
| `test_udp_packetizer_perf.py` | `udp_packetizer_perf_v2_jumbo` |
| `test_udp_packetizer_perf.py` | `udp_packetizer_perf_v2_std` |
| `test_variable_rate_perf.py` | `variable_rate_perf_linkedGetRate` |
| `test_variable_rate_perf.py` | `variable_rate_perf_linkedSetRate` |
| `test_variable_rate_perf.py` | `variable_rate_perf_localGetRate` |
| `test_variable_rate_perf.py` | `variable_rate_perf_localSetRate` |
| `test_variable_rate_perf.py` | `variable_rate_perf_remoteGetRate` |
| `test_variable_rate_perf.py` | `variable_rate_perf_remoteSetNvRate` |
| `test_variable_rate_perf.py` | `variable_rate_perf_remoteSetRate` |

## `test_block_gil_contention_perf.py`

### 1. What the name and docstring claim

The module carries no Python module docstring (no top-level triple-quoted string). The
closest analog is its top-of-file comment block, which is unusually detailed for this
directory and is quoted here in full intent: it says the test "reproduces SLAC rogue #1262:
the v6 update-queue drain stalls because `Block::getBytes` / `Block::setBytes` released the
Python GIL unconditionally on every call," that a bulk drain of "~42k staged variable
updates" costs "~42k `PyEval_SaveThread`/`PyEval_RestoreThread` cycles," and that "pre-fix the
contended drain blows past the ceiling; post-fix the uncontended fast path keeps the GIL and
the drain stays fast." The function name is
`test_block_getset_drain_under_gil_contention`, and the module lives under `tests/perf/`
tagged `pytest.mark.perf`.

### 2. What the code actually measures

Two timed regions, each wrapping only the call to `_drain(var, DRAIN_COUNT)`: a baseline
drain with no contending thread, then a second drain of the same `DRAIN_COUNT = 42000`
iterations while a busy pure-Python thread (`_spawn_gil_contender`) is running and contending
for the GIL. `_drain` performs `var.set(i & 0xFFFFFFFF, write=False)` and
`var.get(read=False)` per iteration, i.e. the pure `Block::setBytes`/`Block::getBytes` path
with no hardware transaction issued, so the Block mutex is never contended and the only
variable under test is GIL hand-off cost. Both timings use `time.perf_counter()`. The
published fields are `drain_count`, `baseline_s`, `contended_s`, `slowdown_ratio` (
`contended_s / baseline_s`), `ceiling_s`, and `threshold_pass`; all four numeric fields are
wall-clock seconds or a dimensionless ratio of two wall-clock seconds.

### 3. The gap

The name and header comment are accurate: the module measures exactly what it says it
measures, a getBytes/setBytes drain under GIL contention, reproducing a named, cited
regression. There is no naming or docstring gap here.

### 4. What it asserts

`assert threshold_pass`, where `threshold_pass = contended_s < CEILING_S` and
`CEILING_S = 10.0`. This is a wall-clock threshold assertion in form (it compares a measured
duration against a fixed constant), but see the recorded disposition for how that constant's
role is characterized relative to the stall it was added to catch.

The published series carries `primary_metric: null`: `_metric_descriptor` in
`scripts/perf_data.py` recognizes only `avg_ns` and `throughput_mb_s`, and this module emits
neither, so its measured `slowdown_ratio` (and `contended_s`, `baseline_s`) is invisible to
the current comparison tooling even though it is faithfully published every run.

### Observed measurement-design notes

Each of `baseline_s` and `contended_s` is a single, unrepeated measurement of one 42000-call
drain with no warmup pass, so any one-off host hiccup during either half is indistinguishable
from a real slowdown in the published pair; diagnosing whether that single-sample design
contributes to run-to-run noise is out of scope here.

## `test_fifo_perf.py`

### 1. What the name and docstring claim

No module docstring. The title comment reads "FIFO stream performance test," and an inline
comment above the workload constants says: "Preserve the original larger FIFO workload as the
recorded soak benchmark." The function is `test_fifo_path`.

### 2. What the code actually measures

The timed region starts at `start = time.perf_counter()`, immediately before a loop that
calls `prbs_tx.genFrame(FRAME_SIZE)` `FRAME_COUNT = 10000` times, and continues through a
polling loop (`FRAME_DRAIN_POLLS = 300` iterations of `time.sleep(FRAME_DRAIN_INTERVAL)`,
`FRAME_DRAIN_INTERVAL = 0.1`) that waits for `prbs_rx.getRxCount() == FRAME_COUNT`. `elapsed`
is read immediately after that loop exits (by count match or by exhausting all 300 polls).
The published `throughput_mb_s` field is
`((received * FRAME_SIZE) / (1024.0 * 1024.0)) / elapsed`, i.e. megabytes per second computed
over that whole generate-plus-drain-wait window, not over frame generation alone. Published
fields: `frames_sent`, `frames_received`, `frame_size`, `elapsed_sec`, `throughput_mb_s`,
`rx_errors`, `drain_complete`.

### 3. The gap

The name and header comment call it a soak/throughput benchmark, which matches: it does
measure and publish `throughput_mb_s`. But nothing in the module asserts a threshold on that
throughput; every assertion is a correctness check (see below), so despite living under
`tests/perf/` and computing a rate, this module enforces no performance regression gate at
all today, only a functional one.

### 4. What it asserts

Three assertions, all functional: `received > 0`, `errors == 0`, and
`received == FRAME_COUNT`. None compares a measured duration or rate to a threshold.

### Observed measurement-design notes

The drain-wait loop's `time.sleep(0.1)` polling granularity is included inside the timed
`elapsed` window, so every published `elapsed_sec` (and therefore every `throughput_mb_s`)
carries up to a 0.1 s quantization step from poll timing on top of the actual transfer time.

## `test_stream_bridge_perf.py`

### 1. What the name and docstring claim

No module docstring. The title comment reads "Data over stream bridge test script," and the
inline comment above the workload constants says: "Keep the original larger payload here so
this file serves as a soak / throughput-style benchmark rather than a correctness-focused
regression test." The function is `test_data_path`.

### 2. What the code actually measures

Structurally identical to `test_fifo_perf.py` but over a real TCP loopback bridge
(`rogue.interfaces.stream.TcpServer`/`TcpClient`) instead of an in-process FIFO. The timed
region starts at `start = time.perf_counter()` before the `FrameCount = 10000` frame
generation loop and continues through a `time.sleep(.1)`-polling drain-wait loop of up to 200
iterations. `elapsed` is read immediately after. `throughput_mb_s` is computed the same way as
`fifo_perf`. Published fields: `frames_sent`, `frames_received`, `frame_size`, `elapsed_sec`,
`throughput_mb_s`, `rx_errors`, `drain_complete`.

### 3. The gap

The name and header comment are accurate as a description of what is measured (a bridged
stream throughput soak). One difference from its own header framing: the header explicitly
disclaims being "a correctness-focused regression test," yet its only assertions are
correctness checks, so in practice it is exactly that plus an unenforced throughput
measurement, not something distinct from `fifo_perf`'s pattern.

### 4. What it asserts

Two assertions, both functional: `received > 0` and `errors == 0`. Unlike `fifo_perf`, there
is no assertion that `received == FrameCount`, so a drain that times out having received only
part of the traffic without error is not itself a failure so long as at least one frame
arrived.

### Observed measurement-design notes

As in `fifo_perf.py`, the drain-wait poll loop's `time.sleep(.1)` granularity is folded into
the timed `elapsed` window used to compute `throughput_mb_s`.

## `test_udp_packetizer_perf.py`

### 1. What the name and docstring claim

No module docstring. The title comment reads "Data over udp/packetizer/rssi test script," and
the inline comment above the workload constants says: "Keep the original larger workload here
so this file remains a meaningful soak / throughput benchmark for the UDP/RSSI/packetizer
stack." The function is `test_data_path`, which calls `data_path` four times
(`ver` in `{1, 2}` crossed with `jumbo` in `{True, False}`), producing the module's four
published series.

### 2. What the code actually measures

A full UDP/RSSI/packetizer (v1 `Core` or v2 `CoreV2`) round trip with an injected
out-of-order module on the outbound path. The timed region starts at
`start = time.perf_counter()` before the `FrameCount = 10000` frame generation loop, then
waits for drain via a `time.sleep(0.1)`-polling loop bounded by `DrainTimeout = 30.0`
seconds. Unlike `fifo_perf.py` and `stream_bridge_perf.py`, `elapsed` is read only after
`cRssi._stop()` and `sRssi._stop()` have both been called to tear down the RSSI connections,
so `elapsed` includes connection-teardown latency in addition to frame generation and drain
wait. `throughput_mb_s` is computed the same way as the other two throughput modules.
Published fields: `version`, `jumbo`, `frames_sent`, `frames_received`, `frame_size`,
`elapsed_sec`, `throughput_mb_s`, `rx_errors`, `drain_complete`.

### 3. The gap

The name and header comment accurately describe a UDP/RSSI/packetizer soak benchmark across
both packetizer versions and both jumbo settings. No naming gap; the timing-boundary
difference noted above (teardown inside the timed region) is a measurement-design detail, not
a claim-versus-behavior mismatch.

### 4. What it asserts

Two assertions per invocation, both functional: `received > 0` and `errors == 0`, plus an
earlier `AssertionError` raised directly (not via `assert`) if the RSSI connection does not
open within 10 one-second polls. As with `stream_bridge_perf.py`, there is no exact
frame-count assertion, so a partial, error-free drain that hits `DrainTimeout` still passes.

### Observed measurement-design notes

`elapsed` is measured after `cRssi._stop()`/`sRssi._stop()` execute, so RSSI connection
teardown cost is folded into every published `throughput_mb_s` for this module, unlike the
other two throughput modules which stop the clock immediately after the drain-wait loop.

## `test_variable_rate_perf.py`

### 1. What the name and docstring claim

No module docstring; the file opens with the standard license header followed only by the
unrelated inline comment "Comment added by rherbst for demonstration purposes." There is no
prose anywhere in the module stating what it measures beyond the function name `test_rate`
and the seven operation-name keys (`remoteSetRate`, `remoteSetNvRate`, `remoteGetRate`,
`localSetRate`, `localGetRate`, `linkedSetRate`, `linkedGetRate`) in the `operations` dict.

### 2. What the code actually measures

`_measure_operation` times `BENCH_COUNT = 100000` calls to one PyRogue variable operation
(remote/local/linked get or set) wrapped in a single `root.updateGroup()` context, once per
operation name. It records `elapsed_ns` via `time.perf_counter_ns()` around the whole loop,
and, when `HAS_HWCOUNTER` is true (the `hwcounter` package installed on Linux x86_64), a raw
CPU cycle count via `hwcounter.count()`/`hwcounter.count_end()` around the same loop. Critically,
`avg_ns` is per-operation (`elapsed_ns / count`), but `cycles` is the raw whole-loop total and
is never divided by `count`: the two published numbers for the same run live at different
granularities in the same record. Published fields per series: `benchmark`, `avg_ns`,
`rate_hz`, `cycles` (when available), `threshold_pass`, `max_avg_ns`, `max_cycles`.

The module defines two threshold tables: `MaxCycles`, a whole-loop cycle ceiling per
operation ("pre-existing tuned thresholds from the original x86/hwcounter-based test"), and a
derived `MaxAvgNs`, computed from `MaxCycles` by assuming a fixed `NOMINAL_CPU_HZ = 3.0e9` and
dividing by `BENCH_COUNT`. Which one governs the actual pass/fail decision on a given host
depends entirely on `HAS_HWCOUNTER`: the comparison at line 188
(`result['cycles'] > MaxCycles[name]`) is live whenever `hwcounter` imports successfully, and
the comparison at line 193 (`result['avg_ns'] > MaxAvgNs[name]`) is reachable only in the
`elif` branch taken when `HAS_HWCOUNTER` is false. `hwcounter` carries a
`platform_system == "Linux" and platform_machine == "x86_64"` marker in both
`pip_requirements.txt` and `pip_requirements_ci.txt`, and the perf job runs on
`ubuntu-24.04` (Linux x86_64), so the cycles comparison at line 188 is the one that actually
gates CI today; the `MaxAvgNs` branch at line 193 is dead code on that runner.

### 3. The gap

The module name (`test_variable_rate_perf.py`) and function name (`test_rate`) are accurate
at face value: it measures the rate of seven kinds of PyRogue variable get/set operations.
But there is no docstring or comment stating that the live gating comparison is a raw,
un-normalized cycle count rather than a per-operation time, nor that a second, seemingly
equivalent ns/op threshold exists but is unreachable on the CI runner. A reader who assumes
`MaxAvgNs` governs CI would be wrong.

### 4. What it asserts

`assert not failures`, an aggregate over all seven operations, where each operation fails
independently against whichever branch (`MaxCycles` or `MaxAvgNs`) is live. This is a
performance threshold assertion, not a functional check: no correctness property of the
measured operations is asserted anywhere in this module.

### Observed measurement-design notes

Each operation is timed as a single unrepeated pass through `BENCH_COUNT` iterations with no
separate warmup pass before the timed loop starts, so any one-time first-call cost (attribute
lookup caching, lazy initialization inside the PyRogue tree) is amortized into, rather than
excluded from, the reported `avg_ns` and `cycles` totals.

## Closing observation

The perf job installs its Python dependencies with `pip install -r pip_requirements.txt` and
no lockfile, so package versions were free to drift across every run represented in the
published series analyzed here. This is recorded as an uncontrolled variable in the
measurement environment, not as a decision made by this work.
