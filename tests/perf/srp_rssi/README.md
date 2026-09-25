# Hardware-free SRP / RSSI burst diagnostic

This opt-in performance/integration experiment uses the real C++
`SrpV3 -> PacketizerV2 -> RSSI -> transport -> RSSI -> PacketizerV2 ->
SrpV3Emulation` path. It borrows the data-integrity/concurrency contract of
`tests/protocols/test_srpv3_concurrent.py` and the client/server connection of
`tests/integration/test_rssi_loopback.py`. The native workload excludes Python;
optional PyRogue workloads exercise the real device/block machinery over the
same asynchronous stack. It is not an automatic timing gate.

See [FINDINGS.md](FINDINGS.md) for the demonstrated backpressure dependency,
the targeted fix, and a concise summary of the revision comparisons.

Two C++ worker queues copy datagrams in opposite directions. Copies are
essential: RSSI retains transmitted frames for retransmission, while receive
processing consumes headers and buffers. Direct synchronous wiring would also
allow receive reentrancy on transmit threads. Both UDP and in-process modes
use Rogue's existing asynchronous emulator, Packetizer transmit workers, and
per-destination Packetizer receive workers (each with an eight-frame queue).

## Build and run

Locate Miniforge and activate the existing `rogue_build` environment as described
in `AGENTS.md`. Do not create or refresh environments just to run this diagnostic.
From the repository root:

```sh
python tests/perf/srp_rssi/build.py
python tests/perf/srp_rssi/run.py --output build/srp-rssi/baseline
python tests/perf/srp_rssi/run.py --windows 600 --sizes 4 4096 \
  --modes app srp tx submit ack --repeat 2 --output build/srp-rssi/delays
python tests/perf/srp_rssi/run.py --windows 600 --sizes 4 4096 \
  --workers 4 --modes none submit tx --repeat 2 --output build/srp-rssi/concurrent
python tests/perf/srp_rssi/run.py --variants before after queue-reverted rssi-reverted \
  --windows 64 600 --sizes 4 4096 --repeat 2 --output build/srp-rssi/isolation
```

`build.py` exports committed sources without switching branches, modifying the
index, or installing libraries. It applies probes to the exported sources only
and by default builds a static no-Python executable using the revision's CMake
build. `--python` instead builds the exported Rogue Python module.
The same native harness and overlay are used for every revision. Its text
anchors fail explicitly if a source layout is unsupported. Rebuilding replaces
only that variant's generated `source/` directory. Build logs and provenance are
under `build/srp-rssi/<variant>/`.

Variants:

- `before`: `b1a669c965^` (`acd6389dfe2ac2a8d13cc7330097207852d79d1b`).
- `after`: `b1a669c965a1d5448cf515fd4ef74e723f99a0f8`.
- `queue-reverted`: after, with the parent's `Queue.h` (non-atomic busy flag).
- `rssi-reverted`: after, with the parent's RSSI Controller header and the two
  counter `.load()` calls adapted to plain integers. Updated log formats remain.
- `current`: the current committed `HEAD`, if supported by the probe anchors.
- `baseline`: the revision supplied with `--baseline-ref`, for comparisons that
  remain reproducible after committing a fix.
- `working`: `HEAD` plus tracked changes under `src/` and `include/` from the
  working tree. The export saves `working.patch` and its SHA-256 in provenance.
  New untracked production files are not included. Use a separate build root
  to compare a candidate fix with `current` without staging or committing it.

Defaults are 600 reads per case, response data sizes 4, 256, 4096 bytes, windows
1, 2, 8, 24, 64, 256, 600, CRC enabled, 1400-byte RSSI segments, and unchanged RSSI
settings (32 segment window, 20 ms retransmit, 5 ms cumulative ACK). SRP responses
include another 24 bytes before Packetizer/RSSI overhead. A 4096-byte read
therefore exercises fragmentation. The window is a **fixed burst limit**, not a
rolling window: submit up to N independent transactions, then wait for that
burst. Window 1 is sequential. Distinct pages are initialized before timing;
every read byte is checked against a deterministic page-specific pattern.

`--workers 4` submits each fixed burst from four concurrent threads through one
SRP client. `--split` instead sends one large memory request through `Hub`, with
4096-byte children sharing the parent mutex. This is a separate diagnostic:
its `--window` is a label, not an enforced child limit. Use size 4096 for full
split-request data validation.

Run experiments serially, without concurrent builds or other test campaigns.
The runner alternates revision order on successive repetitions. Inspect the
range of repeated results; these are host scheduling measurements, not a
statistical guarantee about deployment performance.

## Controlled delays

`--delay-ms` defaults to 200. One delay fires after initialization per case.
`--stall-after N` selects the Nth matching call (default 1; does not apply to
the ACK script):

| Mode | Injection point | Purpose |
| --- | --- | --- |
| `app` | Host RssiApp after dequeue, before downstream send | Stop the RSSI application consumer |
| `srp` | Host SrpV3::acceptFrame entry on PackApp | Stop the Packetizer application worker; its eight-frame queue then backpressures RssiApp |
| `tx` | Host RSSI applicationRx entry on Packetizer transmit thread | Stop request transmission independently of reception |
| `submit` | SrpV3::doTransaction after sendFrame | Positive control for a response waiting on its submitting transaction in revisions that still hold the transaction lock here |
| `ack` | Peer-to-host datagram worker freezes ACK, clears BUSY, recomputes checksum | Script ACK starvation with BUSY clear |

The `submit` hold is deliberately artificial and is not evidence of a naturally
occurring 200 ms critical section. With four workers, other requests continue
while the first response waits for the held lock on PackApp. RssiApp then blocks
in the full Packetizer receive queue, not directly in SRP.
If a candidate fix releases the lock before sending, this injection no longer
holds a transaction lock and must not be interpreted as the same positive control.

The ACK script rewrites packets, not the peer's internal ACK state. Once the
freeze ends, normal headers resume on the next peer transmission. This can
leave ACK restoration waiting for a NULL heartbeat, even after the delay has
expired. Use `--retran-ms 200` to distinguish recovery with more retry budget
from the default 20 ms reset path. It models the observed wire symptom, not an
identified FPGA implementation defect. `ack` is supported only with in-process
transport.

Potentially blocked submissions are bounded by a 12-second native watchdog,
which saves committed trace records then exits 124; the runner also has an
18-second process deadline. Memory timeouts alone cannot bound a blocked
`reqTransaction`. Each case is a fresh process. The harness stops RSSI and its
wire workers, then exits explicitly because old revisions have ownership cycles
and differing worker teardown APIs. This does not validate library teardown.

## Trace format and analysis

The native buffer reserves two million records and reports overflow. It uses
`steady_clock` nanoseconds and a relaxed atomic slot reservation; record
publication uses release/acquire semantics for safe watchdog dumps. Formatting
and CSV writes occur after measurement. There is no per-packet logging.
Instrumentation still adds clock/atomic/cache traffic; compare `--no-trace`
cases before interpreting small timing differences. `Scope` clock reads remain
in no-trace builds, so that is a reduced-probe control, not an unmodified binary.

CSV columns: `ns,thread,event,object,a,b,c`. Pointers are process-local identities.
Sort by `ns` across threads; row reservation order need not equal timestamp order.

- `rssi_queue`: object = controller; a = queue identity; b = server flag.
- `host_app`, `host_srp`, `host_packet_app`: identify the host callback objects.
- `packet_app_queue`: object = Packetizer application; a = its queue identity,
  b = destination. `queue_full_wait_begin/end` bracket blocking condition-variable
  waits at the bounded queue. `packet_app_push` brackets pushFrame;
  `packet_app_callback` brackets downstream sendFrame on the PackApp worker.
- `wire_arrival`: a = packet bytes; b = peer-to-host direction.
- `queue_push/pop`: depth and threshold BUSY captured while holding the queue
  mutex; pair FIFO enqueue/pop events to obtain residence time.
- `rssi_rx/tx`: a = 8-bit sequence, b = 8-bit ACK, c = BUSY bit 0, RST bit 1,
  SYN bit 2, NULL bit 3. `ack_rx` records the applied peer ACK.
- `rssi_dequeue`: a = sequence whose dequeue advances the outgoing ACK;
  b = NULL flag. ACK/dequeue progress is not SRP completion.
- `local_busy`: sampled BUSY state transition. Queue BUSY and advertised BUSY
  are distinct; wire headers are the evidence for what the peer sees.
- `rssi_callback`, `packet_rx`, `packet_callback`, `srp_callback`,
  `srp_submit`, `rssi_send`: a=0 entry, a=1 exit with b=duration in ns.
- `packet_queue_wait_begin/end`: outbound Packetizer busy-wait boundaries.
- `rssi_window_wait`: scope beginning before RSSI transmit-window polling,
  ending at applicationRx return; includes final transport send overhead.
- `srp_request`: transaction ID and data size; `srp_response`, `srp_done`: ID.
- `map_lookup`: requested response ID. `map_lock_wait/acquired` and
  `map_get/add` record pending-transaction map mutex waits and call duration.
- `refresh_wait/acquired`: a = transaction ID whose mutex is requested;
  b = reference/response ID. Different IDs expose cross-transaction timer-refresh
  blocking before SRP takes the response's own lock. The map mutex remains held
  during refresh when called by getTransaction.
- `lock_wait/acquired/release`: object = root transaction object, a = root ID.
  Subtransactions therefore expose their shared lock identity. These probes
  measure TransactionLock acquisition, not every mutex in the stack.
- `retransmit`: sequence and prior transmission count. `reset_retry_limit`,
  `reset_peer`, `reset_shutdown` distinguish reset causes; `reset` marks action.
- `measure_begin/end`, `stall_begin/end`, `ack_freeze_begin/end`, `watchdog`:
  experiment boundaries and injected fault events.

`run.py` writes case logs, CSV traces, environment metadata, and `results.json`
with maximum/median/p99 durations and a timeline of long callbacks, lock waits,
BUSY transitions and resets. It returns nonzero for failed data/completion cases;
ACK fault experiments may intentionally do so. Queue residence assumes FIFO
without reset; do not interpret the residence estimate across a reset. Native
CSV retains the evidence needed to inspect those cases directly.

```sh
python tests/perf/srp_rssi/plot.py build/srp-rssi/delays/after-4-600-srp-0.csv \
  --output build/srp-rssi/timeline.svg
```

## Separate scheduling experiments

```sh
python tests/perf/srp_rssi/run.py --windows 1 600 --sizes 4 4096 \
  --transport udp --retran-ms 200 --repeat 1 --output build/srp-rssi/udp
python tests/perf/srp_rssi/run.py --windows 1 600 --sizes 4 4096 \
  --no-trace --output build/srp-rssi/untraced
```

UDP loopback is explicit opt-in on macOS, consistent with the existing suite's
skip for timing sensitivity. Neither in-process nor macOS UDP establishes Linux
bench timing. GHDL is intentionally not used for host timing; it remains useful
for firmware correctness.

For lower-overhead queue-only measurements, build with `--no-timer-probes`.
The initial investigation used this option; default full probes additionally measure
transaction-map and timer-refresh locks. To exercise cross-transaction locking:

```sh
python tests/perf/srp_rssi/run.py --windows 600 --sizes 4 4096 \
  --modes tx --stall-after 8 --repeat 2 --output build/srp-rssi/tx-late
python tests/perf/srp_rssi/run.py --windows 600 --sizes 4 4096 \
  --modes submit --stall-after 2 --workers 4 --repeat 2 --output build/srp-rssi/refresh-lock
```

An optional threshold sensitivity build uses a different output root:
`build.py --variants after --threshold 8 --output build/srp-rssi-threshold8`.
Run it with `run.py --build-root build/srp-rssi-threshold8 --variants after ...`.
A threshold improvement alone is not a causal diagnosis.

## Warm-TDM transport and actual PyRogue blocks

The follow-up shares `Stack.h` between the native executable and a private
`rogue._BurstStack` binding compiled only into exported diagnostic trees. Native
builds stay `NO_PYTHON=1`; Python builds use that revision's real Rogue extension
and PyRogue sources. Keep these in separate output directories:

```sh
python tests/perf/srp_rssi/build.py --variants before after \
  --output build/srp-rssi-warm-native
python tests/perf/srp_rssi/build.py --variants before after --python \
  --output build/srp-rssi-warm
python tests/perf/srp_rssi/run.py --build-root build/srp-rssi-warm-native \
  --segment 1024 --rssi-window 8 --repeat 2 \
  --output build/srp-rssi-warm-native/native-control
python tests/perf/srp_rssi/run.py --build-root build/srp-rssi-warm \
  --workload blocks --segment 1024 --rssi-window 8 --repeat 2 \
  --output build/srp-rssi-warm/blocks-control
```

`--workload blocks` creates a real Root/Device/RemoteVariable tree and calls the
historical `pr.readAndCheckBlocks()` helper on deduplicated dependency blocks
inside `root.updateGroup()`. This follows Warm-TDM's grouped dependency-block
read/check pattern. `--workload device` instead uses each device's `readBlocks()`
and `checkBlocks()` methods. Both traverse real C++ Block/Hub/Transaction paths.
The register map is a synthetic set of distinct pages, not the entire deployed
Warm-TDM tree. Each case still has 600 reads unless `--count` is changed.

The reader has read-only scalar or array blocks. A separate initialization tree
writes known data over the same transport and stops before the reader starts;
reader caches are checked to be zero. Every returned word must match the peer's
pattern. Simply staging zero into an RW reader would mark its block stale and
cause Rogue to skip the read. The fixture explicitly avoids that false pass.
Initialization and teardown are outside the measured interval. Python elapsed
time includes grouped updates and cached-value validation as well as reads;
use the native timeline for individual queue/lock durations.

The requested segment size and window are set on both RSSI endpoints.
`negotiated_host/peer` events record the actual negotiated segment/window, so
configuration can be checked independently of command-line intent. Default
1400/32 remains available for comparison; use explicit 1024/8 here.
The native watchdog covers initialization and reads; the Python watchdog begins
at the measured reads. Both save traces on blocked native submission. The
runner allows 45 seconds for a Python process (including building its tree),
versus 18 seconds for a native process.

## Finite peer queues without injected delays

```sh
python tests/perf/srp_rssi/run.py --build-root build/srp-rssi-warm-native \
  --segment 1024 --rssi-window 8 --peer-requests 1 --peer-responses 1 \
  --windows 24 64 256 600 --sizes 4096 --repeat 2 \
  --output build/srp-rssi-warm-native/native-bounded
python tests/perf/srp_rssi/run.py --build-root build/srp-rssi-warm \
  --workload blocks --segment 1024 --rssi-window 8 \
  --peer-requests 1 --peer-responses 1 \
  --windows 24 64 256 600 --sizes 4096 --repeat 2 \
  --output build/srp-rssi-warm/blocks-bounded
```

These commands use mode `none`; watchdog exit 124 is a captured persistent
stall, and `run.py` deliberately returns nonzero for it. It continues the rest
of its matrix and retains results. Do not treat a watchdog as a passing
correctness test. These commands compare the unfixed April revisions.

`--peer-requests N` limits pending frames in SrpV3Emulation's request queue; one
additional request can be processing. Acceptance waits on its condition
variable when full. `--peer-responses N` gives the **peer's** Packetizer transmit
queue both capacity and BUSY threshold N, measured in response segments. It
blocks the emulator's single processing worker when response transmission
cannot drain. This couples request acceptance to reply progress using real
queue waits; there is no artificial service delay. Host queue settings remain
unchanged. At zero, the respective added limit is disabled; the peer's original
transmit BUSY threshold of 64 still applies even with no hard capacity limit.

Run request-only (1/0), response-only (0/1), and larger-capacity (8/8) controls by
changing those two flags. These are sensitivity models, not measured FPGA FIFO
depths. Datagram transport still has separate asynchronous receive workers.
The model omits the FPGA's missing-BUSY fault unless the separate ACK script is
explicitly selected in a native run.

Additional trace fields:

- `transport_config`: a=segment bytes, b=RSSI window, c=retransmit milliseconds.
- `negotiated_host/peer`: a=negotiated segment bytes, b=negotiated window.
- `packet_tx_queue`: object=Packetizer controller, a=queue, b=hard capacity,
  c=peer flag. Host capacity zero means unbounded with original BUSY threshold.
- `peer_request_push/pop`: pending depth; push also records configured limit.
- `peer_request_wait_begin/end`: wait for pending-request space.
- `peer_process`: emulator processing callback, including blocked response send.
- `rssi_window_enter/ready`: a=outstanding segments, b=negotiated window.

Summaries retain unfinished transaction holds, timer/map waits, RSSI window
waits, queue-capacity waits, callback scopes, last RSSI dequeue times, measured
request/completion counts, and fault/retransmission/reset counts. Watchdog traces
therefore retain the blocked interval rather than reporting only completed
fast calls. A plot's dashed lock-wait line means still waiting at capture end:

```sh
python tests/perf/srp_rssi/plot.py \
  build/srp-rssi-warm-native/native-bounded/after-4096-256-none-0.csv \
  --until-ms 20 --output build/srp-rssi-warm/native-onset.png
```
