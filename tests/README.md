# Test Suite Layout

This README documents the test layout in `tests/`. The Python and native C++
tests are organized by behavior and execution style rather than by history.

Directories:

- `core/`: deterministic PyRogue tree/runtime behavior
- `interfaces/`: client/server wrappers and interface helpers
- `fileio/`: file and stream reader/writer behavior
- `protocols/`: protocol-specific deterministic tests
- `integration/`: real transport, socket, and environment-dependent tests
- `perf/`: soak, throughput, and benchmark-style tests
- `utilities/`: helper and exporter modules
- `cpp/`: native C++ unit and smoke tests driven by `ctest`

Other top-level files:

- `conftest.py`: shared pytest fixtures and helpers
- `test_config_out.yml`: generated/config fixture output used by tests

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
- Keep fast deterministic native coverage in `tests/cpp/` and reserve
  socket-backed or long-running native scenarios for a later labeled expansion.

Common commands:

- Standard build tree:
  - Configure/build into the repo-local `build/` directory with
    `cmake -S . -B build ...`
  - Run both Python and Python-enabled native C++ tests from that same
    `build/` tree after sourcing `build/setup_rogue.sh`
  - Add `-DROGUE_BUILD_TESTS=ON` when you want the native C++ suite built in
    that tree

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
- Performance subset with result export:
  - `PERF_RESULTS_DIR=perf-results pytest tests/perf -q -s`
- Python-enabled native C++ smoke subset:
  - `source build/setup_rogue.sh`
  - `ctest --test-dir build --output-on-failure -L requires-python`
- Deterministic native C++ subset in a dedicated `-DNO_PYTHON=1` build:
  - See `cpp/README.md` for the required reconfigure/build step and
    `ctest --test-dir build --output-on-failure -L no-python`

Planning / handoff docs:

- `BRANCH_STATUS.md`: summary of the current branch state, including the native
  C++ suite status
- `NEXT_STEPS.md`: likely follow-up work and wrap-up checklist for both the
  Python and native C++ suites
- `cpp/README.md`: native C++ suite layout, labels, and commands
