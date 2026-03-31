# Test Suite Layout

The Python tests are organized by behavior and execution style rather than by
history.

Directories:

- `core/`: deterministic PyRogue tree/runtime behavior
- `interfaces/`: client/server wrappers and interface helpers
- `fileio/`: file and stream reader/writer behavior
- `protocols/`: protocol-specific deterministic tests
- `integration/`: real transport, socket, and environment-dependent tests
- `perf/`: soak, throughput, and benchmark-style tests
- `utilities/`: helper and exporter modules

Guidelines:

- Keep focused unit-style behavior tests in the most specific subsystem
  directory.
- Keep real transport or socket-backed tests in `integration/`, even when the
  asserted behavior is narrow.
- Keep long-running or host-sensitive performance workloads in `perf/` instead
  of the default regression path.
- Preserve layered coverage. A core behavior test and an integration test may
  both exist if they validate different levels of the stack.
- Prefer file names that describe the behavior under test, not just one data
  type or one implementation detail.

Common commands:

- Fast deterministic suite:
  - `pytest -m "not integration and not epics and not perf" -q`
- Core subset:
  - `pytest tests/core -q`
- Interfaces subset:
  - `pytest tests/interfaces -q`
- Integration subset:
  - `pytest tests/integration -q`
- Performance subset:
  - `pytest tests/perf -q`

Planning / handoff docs:

- `BRANCH_STATUS.md`: summary of the current branch state and major changes
- `NEXT_STEPS.md`: likely follow-up work and wrap-up checklist
