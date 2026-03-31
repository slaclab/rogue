# Next Steps

This document captures the likely follow-up work after the current branch
state. It is meant to be short and actionable rather than exhaustive.

## Immediate Recommended Checks

Before doing more edits, rerun the known baseline commands in a fresh build:

- Fast deterministic suite:
  - `pytest -m "not integration and not epics and not perf" -q`
- Full unsandboxed Python suite:
  - `python -m pytest --cov`
- Integration-only subset:
  - `pytest tests/integration -q`
- Interface integration subset:
  - `pytest tests/interfaces/test_interfaces_virtual_integration.py tests/interfaces/test_interfaces_simple_client_integration.py -q`

If local runs fail with a compiled-version mismatch, rebuild/install Rogue
before debugging test logic.

## Highest-Value Remaining Work

### 1. Let CI settle, then decide whether to keep xdist coverage

Recent CI changes:

- `pytest-xdist` was added to `pip_requirements.txt`
- `.github/workflows/rogue_ci.yml` now uses:
  - `python -m pytest -n auto --dist loadfile --cov`

Next step:

- let CI run a few times
- compare runtime and stability against the known serial baseline
- only change the command shape again if xdist exposes real flakiness

### 2. Rebuild and confirm the ZMQ timeout log suppression

`src/rogue/interfaces/ZmqClient.cpp` now uses a debug log call instead of
printing timeout configuration to stdout.

Next step:

- rebuild Rogue
- rerun the live ZMQ integration tests
- confirm the old `ZmqClient::setTimeout` lines are gone from test output

### 3. Decide whether to do any more high-value integration additions

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

### pydm / example / gpib / hls parser coverage

These were intentionally not prioritized. Only take them on if there is a real
product reason, not just to raise the total percentage.

## Branch Wrap-Up Checklist

If the goal is to finish this branch rather than expand it further:

1. Rebuild Rogue in the target CI/local environment.
2. Rerun the fast deterministic suite.
3. Rerun the full unsandboxed Python suite with coverage.
4. Confirm the xdist CI job is stable enough.
5. Confirm the SQL logging test is stable in CI.
6. Confirm the ZMQ timeout spam is gone after rebuild.
7. Refresh any PR description / summary text if needed.

At that point the branch is likely ready to wrap unless a specific missing
integration scenario becomes important.
