# Root Operation Shared Gate Progress

## Implemented

- Added a private writer-preferred shared/exclusive gate owned by `Root`.
- Routed public `Root.operationLock()` through reentrant exclusive admission.
- Added shared admission to built-in RemoteVariable, LocalVariable, and
  LinkVariable access entry points, including LocalVariable in-place updates.
- Made command invocation and direct RemoteCommand writes exclusive.
- Preserved operation of detached variables by using a no-op context when a
  node has no Root.
- Updated Root operation-lock documentation.
- Added tests covering exclusive blocking, concurrent shared reads, writer
  preference, and reentrant command execution.

## Validation

- Repository build and local install completed in the existing `rogue_build`
  conda environment.
- `17 passed` in `tests/core/test_core_root_device_io_edges.py`.
- `45 passed` across core variables/commands, variable waits, YAML behavior,
  and the ZMQ server tests.
- `13 passed` across core structure and Root tree tests.
- `28 passed` in the final focused Root, command, and ZMQ rerun before the
  writer-preference test was added.
- Python compile checks and `git diff --check` pass.
- Flake8 was not available in the existing `rogue_build` environment, so the
  focused flake8 command could not run.

## Local Cost Measurement

On this macOS development host, a cached `LocalVariable.value()` microbenchmark
measured approximately:

- 2.004 microseconds per call with the shared gate.
- 0.978 microseconds per call with shared admission bypassed.
- 1.026 microseconds incremental gate cost per call.

This is a local implementation-cost measurement, not a CI performance
threshold. Hardware-backed calls will usually be dominated by transaction
latency, while extremely hot cached LocalVariable reads may notice the added
cost.
