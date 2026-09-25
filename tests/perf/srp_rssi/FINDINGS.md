# SRPv3 backpressure stall

Batched SRPv3 reads can stop response processing when request transmission
blocks while holding a transaction mutex. A bounded software peer reproduces
this without injected sleeps through the real RSSI/PacketizerV2/SRP path.
The targeted fix releases that mutex before downstream transmission.

## Dependency and fix

The host submitter holds a request's transaction mutex across `sendFrame()`.
That call can block on Packetizer transmit capacity while the RSSI window is
full. Meanwhile, an earlier response's `Slave::getTransaction()` refreshes
pending transaction timers while holding the transaction-map mutex, and waits
for the later request's transaction mutex.

Response processing runs on Packetizer's PackApp worker. When it stops,
Packetizer's eight-frame receive queue fills. RssiApp then blocks synchronously
in the queue push, holding the receive frame lock and Packetizer receive mutex.
That prevents further RSSI application dequeues and ACK advancement. The RSSI
application queue's two-entry BUSY threshold propagates backpressure to the
peer. Finite, coupled peer request/reply queues can sustain the cycle.

SRPv3 now releases the transaction lock after serialization and response
registration, before sending. The frame owns its data; submission no longer
accesses caller storage after release. Hub also forwards a stable vector of
split children because response completion can erase the pending-child map
during a downstream call. Queue thresholds, atomics, and timer-refresh
semantics are unchanged.

## Local evidence

These results used macOS arm64, asynchronous copied in-process datagrams,
1024-byte RSSI segments, an eight-segment window, and 600 reads per case.
Response data sizes were 4, 256, and 4096 bytes; outstanding limits were
1, 2, 8, 24, 64, 256, and 600. The bounded peer allowed one queued SRP request
plus one active request and one queued response segment. These are model
constraints, not measured FPGA FIFO depths.

| Comparison or control | Result |
| --- | --- |
| Before/after `b1a669c965`, finite peer queues | Both reproduce the timer-refresh dependency; no atomic regression established |
| Unfixed `4dbda87d7`, native and PyRogue blocks, 600 × 4096 bytes, two repetitions each | All four stall until watchdog |
| Fixed, same paired workloads | Native completes in 63–71 ms; PyRogue blocks in 94–142 ms |
| Fixed native and PyRogue full sweeps | 42/42 pass |
| Fixed controls including other peer bounds, concurrent submission, Hub splitting, and reduced event recording | All pass; 58 fixed normal-traffic cases in total |
| Separate 200 ms stalls in RssiApp, SRP callbacks, and request transmission | All recover after release, without reset |
| Scripted ACK starvation with BUSY clear, 20 ms retransmit interval | Still fails with retry-limit reset |
| Same ACK script, 200 ms retransmit interval | Recovers; this is a control, not a proposed setting |

The complete fix campaign had 72 cases: 65 passes, six unfixed watchdogs
(including two reduced-probe runs), and one intentional ACK-fault failure.
The unfixed Device read/check case passed in one paired run; the dependency
does not stall every scheduling instance. These timings are examples, not
statistical performance guarantees.

One unfixed native timeline pinpoints the RSSI consumer stop:

| Time from read start | Event |
| ---: | --- |
| 13.959 ms | Request 812 holds its transaction mutex |
| 13.961 ms | Its submitter waits for Packetizer transmit capacity |
| 13.988 ms | Response 722's timer refresh waits for request 812's mutex |
| 14.242 ms | Last host RSSI application dequeue |
| 14.245 ms | RssiApp blocks on the full eight-frame Packetizer receive queue |
| 11713.928 ms | Watchdog captures the ongoing stall; 121 reads completed |

In the fixed pair, all 600 reads complete in 71.170 ms. The longest submitter
transmit wait is still 3.075 ms, but none of the 600 transmit wait scopes holds
a transaction lock. The longest timer-refresh wait is 0.0205 ms, and RSSI
dequeue progress continues through 71.158 ms. Normal BUSY assertions remain.

The deterministic native regression checks fail with the original lock scope
and pass with the fix. They cover read/write/verify response progress, posted
data ownership, early split-child completion, and timeout/late-response handling.
Ten relevant native executables pass in each Python-enabled and no-Python build,
and the three SRPv3 Python suites pass all 14 tests.

## Reproduce after committing the fix

Activate the existing Miniforge build environment. Build the original baseline
and the committed fix with identical probes, without switching branches:

```sh
python tests/perf/srp_rssi/build.py --variants baseline current \
  --baseline-ref 4dbda87d7fe60f4ced851770e3d37b51b05be619 \
  --output build/srp-rssi-compare-native
python tests/perf/srp_rssi/build.py --variants baseline current --python \
  --baseline-ref 4dbda87d7fe60f4ced851770e3d37b51b05be619 \
  --output build/srp-rssi-compare-python
```

Run campaigns serially, after builds finish:

```sh
python tests/perf/srp_rssi/run.py --build-root build/srp-rssi-compare-native \
  --variants baseline current --windows 600 --sizes 4096 --repeat 2 \
  --segment 1024 --rssi-window 8 --peer-requests 1 --peer-responses 1 \
  --output build/srp-rssi-compare-native/paired
python tests/perf/srp_rssi/run.py --build-root build/srp-rssi-compare-python \
  --variants baseline current --workload blocks --windows 600 --sizes 4096 \
  --repeat 2 --segment 1024 --rssi-window 8 \
  --peer-requests 1 --peer-responses 1 \
  --output build/srp-rssi-compare-python/paired
```

Unfixed watchdog cases make the runner return nonzero; inspect each case's
result rather than treating that campaign as passing. For the fixed full sweep,
select `--variants current --repeat 1` and omit `--windows` and `--sizes`.
The [README](README.md) documents April revision isolation, peer constraints,
fault controls, reduced probes, buffered trace events, and plotting commands.
Generated traces and machine-specific provenance belong under ignored `build/`.

## Scope

The host stall can trigger or amplify separate FPGA failures, but the causal
link to the full bench failure still needs confirmation. The software peer does
not establish the deployed FPGA's queue layout. The PyRogue fixture uses real
blocks and transactions with a synthetic tree, not every Warm-TDM getter.
macOS in-process or localhost UDP timing does not establish Linux bench timing;
GHDL remains useful for firmware correctness, not this real-time comparison.

Bench validation should compare RSSI dequeues, response completion, and ACK/BUSY
progress with the host fix present. FPGA ACK starvation with BUSY clear remains
a separate defect even if removing the host trigger makes it less frequent.
