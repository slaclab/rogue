# Next Steps

This document captures the likely follow-up work for `cpp-tests` relative to
`origin/pre-release`. It is intentionally limited to the native C++ test work
and its immediate CI/doc follow-through.

## Immediate Checks

Before more edits, rerun the native baseline commands in a fresh build:

- Python-enabled native suite:
  - `ctest --test-dir build --output-on-failure -L cpp`
- Dedicated no-Python native subset:
  - reconfigure with `-DNO_PYTHON=1 -DSTATIC_LIB=1`
  - `ctest --test-dir build --output-on-failure -L no-python`

On macOS, make sure the runtime library path points at the active `build/`
tree before debugging unexpected native failures.

## Highest-Value Remaining Work

### 1. Decide whether the full-build CI job should run `-L cpp`

Current state:

- the full-build CI job runs `ctest ... -L cpp`
- the small build job runs `ctest ... -L no-python`

Recommended steady state:

- full build: `ctest --test-dir build --output-on-failure -L cpp`
- small build: `ctest --test-dir build --output-on-failure -L no-python`

If the full-build job does not broaden to `-L cpp`, document the intentional
split clearly in the workflow comments and native test README.

### 2. Keep the native docs aligned with the actual suite

The native suite has already expanded beyond the original V1 scope. When new
tests land, keep these files current:

- `tests/README.md`
- `tests/cpp/README.md`
- `tests/BRANCH_STATUS.md`
- `tests/NEXT_STEPS.md`

### 3. Add the next bottom-up native coverage only if the branch stays open

Most useful next additions:

- memory routing and dispatch behavior through `Hub` and `Slave`
- deterministic protocol transform coverage for batcher and packetizer
- utility/file I/O native coverage such as PRBS and stream zip/unzip

These should stay deterministic and avoid sockets unless the branch explicitly
expands its scope.

## Lower-Priority Follow-Ups

### Native transport-backed tests

Still intentionally deferred:

- RSSI/TCP/UDP socket-backed native tests
- long-running or perf-style native workloads

These should live behind separate labels when added.

### Native suite ergonomics

Possible cleanup items if needed:

- make the full-build and no-Python build instructions more explicit in CI
  comments
- add more label-specific examples once additional native suites exist

## Branch Wrap-Up Checklist

If the goal is to finish this branch rather than expand it further:

1. Rebuild Rogue in the target CI/local environment.
2. Rerun the full-build native C++ suite.
3. Rerun the dedicated no-Python native subset.
4. Decide whether full-build CI should run `ctest ... -L cpp`.
5. Refresh any PR description / summary text if needed.

At that point the branch is likely ready to wrap unless a specific native test
gap becomes important.
