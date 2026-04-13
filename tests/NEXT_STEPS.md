# Next Steps

This document captures the likely follow-up work after the current branch
state. It is meant to be short and actionable rather than exhaustive.

## Immediate Recommended Checks

Before doing more edits, rerun the known baseline commands in a fresh build:

- Fast deterministic suite:
  - `pytest -m "not integration and not epics and not perf" -q`
- Full unsandboxed Python suite:
  - `python -m pytest --cov`
- Python-enabled native C++ suite:
  - `ctest --test-dir build --output-on-failure -L cpp`
- Integration-only subset:
  - `pytest tests/integration -q`
- Interface integration subset:
  - `pytest tests/interfaces/test_interfaces_virtual_integration.py tests/interfaces/test_interfaces_simple_client_integration.py -q`
- Dedicated no-Python native subset:
  - reconfigure with `-DNO_PYTHON=1 -DSTATIC_LIB=1`
  - `ctest --test-dir build --output-on-failure -L no-python`

If local runs fail with a compiled-version mismatch, rebuild/install Rogue
before debugging test logic.

## Highest-Value Remaining Work

### 1. Decide whether the full-build CI job should run `-L cpp`

The native suite now contains both:

- deterministic core tests labeled `cpp-core` and `no-python`
- the Python-enabled smoke subset labeled `requires-python`

Current state:

- the full-build CI job only runs `ctest ... -L requires-python`
- the small build job runs `ctest ... -L no-python`

Next step:

- decide whether the full-build job should broaden to `ctest ... -L cpp`
- if not, document the intentional split clearly in the workflow comments and
  native test README

### 2. Let CI settle, then decide whether to keep xdist coverage

Recent CI changes:

- `pytest-xdist` was added to `pip_requirements.txt`
- `.github/workflows/rogue_ci.yml` now uses:
  - `python -m pytest -n auto --dist loadfile --cov`

Next step:

- let CI run a few times
- compare runtime and stability against the known serial baseline
- only change the command shape again if xdist exposes real flakiness

### 3. Rebuild and confirm the ZMQ timeout log suppression

`src/rogue/interfaces/ZmqClient.cpp` now uses a debug log call instead of
printing timeout configuration to stdout.

Next step:

- rebuild Rogue
- rerun the live ZMQ integration tests
- confirm the old `ZmqClient::setTimeout` lines are gone from test output

### 4. Decide whether to do any more high-value native additions

Possible additions if more bottom-up native coverage is desired:

- memory routing and dispatch behavior through `Hub` and `Slave`
- deterministic protocol transform coverage for batcher and packetizer
- utility/file I/O native coverage such as PRBS and stream zip/unzip

These are incremental, not required to wrap the branch.

### 5. Decide whether to do any more high-value Python integration additions

Possible additions if more end-to-end coverage is desired:

- a broader remote-tree workflow through `VirtualClient`
  - nested browsing
  - command execution
  - multiple listeners
  - update propagation across several nodes
- a focused test around `ZmqServer` include/exclude groups beyond the current
  `NoServe` coverage

These are incremental, not required to wrap the branch.

## Lower-Priority Follow-Ups

### Test naming cleanup

The suite is much cleaner than before, but a few names could still be made more
uniform if desired. This was intentionally deferred until after the larger test
push.

### Interface/stream coverage

Still largely untouched:

- `python/pyrogue/interfaces/stream/_Fifo.py`
- `python/pyrogue/interfaces/stream/_Variable.py`
- `python/pyrogue/interfaces/stream/__init__.py`

This is a reasonable future target if the branch stays open.

### Native transport-backed C++ tests

Still intentionally deferred:

- RSSI/TCP/UDP socket-backed native tests
- long-running or perf-style native workloads

These should stay behind separate labels when added.

### pydm / example / gpib / hls parser coverage

These were intentionally not prioritized. Only take them on if there is a real
product reason, not just to raise the total percentage.

## Branch Wrap-Up Checklist

If the goal is to finish this branch rather than expand it further:

1. Rebuild Rogue in the target CI/local environment.
2. Rerun the fast deterministic Python suite.
3. Rerun the full unsandboxed Python suite with coverage.
4. Rerun the full-build native C++ suite and the dedicated no-Python subset.
5. Decide whether full-build CI should run `ctest ... -L cpp`.
6. Confirm the xdist CI job is stable enough.
7. Confirm the SQL logging test is stable in CI.
8. Confirm the ZMQ timeout spam is gone after rebuild.
9. Refresh any PR description / summary text if needed.

At that point the branch is likely ready to wrap unless a specific missing
integration scenario becomes important.
