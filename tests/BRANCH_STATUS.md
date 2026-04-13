# Branch Status

This document is a handoff summary for the `cpp-tests` branch relative to
`origin/pre-release`. It only describes the native C++ test work and closely
related fixes that are new on this branch.

## Branch Scope

This branch adds an in-tree native C++ regression suite to the main Rogue
build. The goal is fast deterministic coverage of low-level Rogue memory and
stream behavior, plus one small Python-enabled C++ API smoke test.

The branch does not try to expand the already-merged Python test work from the
parent branch. Treat `origin/pre-release` as the source of truth for that
material.

## Structural Changes On This Branch

- Added `ROGUE_BUILD_TESTS` as a top-level CMake option, default `OFF`, so the
  native suite is opt-in for manual builds and explicit in CI.
- Added `enable_testing()` and a `tests/cpp` subtree to the main build.
- Vendored a single-header doctest harness under `tests/cpp/vendor/`.
- Added a shared native test support target with the doctest main and common
  helpers in `tests/cpp/support/`.
- Replaced the old standalone `tests/api_test` executable path with a
  CTest-managed smoke test in `tests/cpp/smoke/`.
- Added native test labels:
  - `cpp`
  - `cpp-core`
  - `no-python`
  - `requires-python`
  - `smoke`

## Current Native Test Coverage

The current deterministic test files are:

- `tests/cpp/core/test_version.cpp`
  - version helper string/component consistency and compare helpers
- `tests/cpp/memory/test_memory_bits.cpp`
  - `copyBits`, `setBits`, and `anyBits` edge cases
- `tests/cpp/memory/test_transaction_block.cpp`
  - block write/read/verify paths and transaction alignment/error behavior
- `tests/cpp/memory/test_variable.cpp`
  - variable geometry, shift/stride/index handling, and typed accessor errors
- `tests/cpp/stream/test_frame_pool.cpp`
  - pool allocation, frame payload accounting, append/clear/min/adjust paths
- `tests/cpp/stream/test_iterator.cpp`
  - iterator traversal, arithmetic, and end-buffer semantics
- `tests/cpp/stream/test_fifo_filter_rate_drop.cpp`
  - FIFO, filter, and rate-drop flow-control behavior

The current Python-enabled smoke file is:

- `tests/cpp/smoke/test_api_smoke.cpp`
  - short asserted public C++ API construction path

## Validation Snapshot

Known validation completed on this branch:

- Python-enabled native smoke subset:
  - `ctest --test-dir build --output-on-failure -L requires-python`
  - result: passed in a Python-enabled build
- Deterministic native core subset:
  - `ctest --test-dir build --output-on-failure -L cpp-core`
  - result: passed in a local native build
- Deterministic no-Python subset:
  - `ctest --test-dir build --output-on-failure -L no-python`
  - result: passed in a `-DNO_PYTHON=1` build

## Product Fixes Found By The Native Tests

This branch exposed and fixed two real product bugs:

- `src/rogue/interfaces/memory/Master.cpp`
  - zero-length `copyBits`, `setBits`, and `anyBits` requests incorrectly ran a
    loop iteration instead of behaving as no-ops
- `src/rogue/interfaces/stream/Pool.cpp`
  - `Pool::~Pool()` repeatedly freed the same queue front without advancing,
    which could corrupt destruction behavior

## CI / Runtime Notes

- The full-build CI job now enables `ROGUE_BUILD_TESTS` explicitly and runs
  `ctest ... -L cpp`.
- The small build job runs `ctest ... -L no-python` in a dedicated
  `-DNO_PYTHON=1` build with `ROGUE_BUILD_TESTS=ON`.
- The macOS build job also enables `ROGUE_BUILD_TESTS` explicitly and runs
  `ctest ... -L cpp`.
- On macOS, local `ctest` runs can pick up an installed Rogue library from
  `lib/` instead of the fresh build tree unless the runtime library path points
  at `build/`.

## Still Deferred

These native areas remain intentionally out of scope for this branch:

- socket-backed native transport tests
- native protocol-transform coverage beyond the current smoke path
- long-running or perf-style native workloads
