# Test Methodology

This guide describes how to choose and write Rogue tests when changing
production code. It is meant for both humans and AI agents working in the
repository.

For project-wide architecture, coding, documentation, and workflow guidance,
read `../DEVELOPMENT.md`.

Use the narrowest test that proves the behavior, then add higher-level coverage
only when the risk crosses a boundary that the narrow test cannot exercise.

## Test Selection

Start from the behavior you changed:

- Pure Python/PyRogue tree behavior: add or update a fast pytest test under
  `tests/core/`, `tests/interfaces/`, `tests/protocols/`, `tests/fileio/`, or
  `tests/utilities/`.
- Python behavior that needs real sockets, transport threads, or multiple
  Rogue components connected together: use `tests/integration/` or mark the
  module with `pytest.mark.integration`.
- Native C++ helper, memory, stream, packetizer, or lifecycle behavior: add a
  doctest-based executable under `tests/cpp/` and register it with
  `rogue_add_cpp_test()`.
- C++ behavior that must also work without Python: label the test `no-python`
  and keep it free of Python, NumPy, and Boost.Python dependencies.
- Public C++ API behavior that relies on a Python-enabled build: label the test
  `requires-python`; do not expect it to run in the small `-DNO_PYTHON=1`
  build.
- Throughput, rate, soak, or host-sensitive timing behavior: put it under
  `tests/perf/` and mark it `pytest.mark.perf`.
- EPICS/PVA-dependent behavior: mark it `pytest.mark.epics` in addition to any
  integration marker.

Good coverage is layered, not duplicated. A production change may need:

- One fast unit-style test that pins the local contract.
- One integration test when the bug involved a real transport, socket lifecycle,
  thread boundary, serialization path, or public multi-component workflow.
- One no-Python native test when the changed C++ code is compiled into the
  small static build.

Avoid adding broad integration tests when a deterministic unit-style test can
prove the same contract. Conversely, do not replace a socket or lifecycle
regression with a mock-only test if the failure depended on real thread or
transport behavior.

## Python Tests

Python tests use pytest. Keep tests deterministic, local, and explicit about
their execution class.

Patterns to follow:

- Prefer focused assertions on public behavior over implementation details.
- Use `MemoryRoot` or local `rogue.interfaces.memory.Emulate` when hardware is
  not required.
- Use the shared `free_tcp_port` and `free_zmq_port` fixtures for socket tests.
  They reserve worker-specific port ranges for xdist.
- Use `wait_until` for asynchronous state changes instead of fixed sleeps.
- Keep root/device lifetimes inside `with root:` blocks so teardown is part of
  the test.
- Name tests after the behavior or regression being protected.
- Use `pytest.mark.parametrize` for meaningful boundary sweeps, especially bit
  widths, offsets, packet sizes, and mode combinations.
- Put module-level markers near the imports:
  `pytestmark = pytest.mark.integration`,
  `pytestmark = [pytest.mark.integration, pytest.mark.perf]`, or similar.

Do not make normal regression tests depend on external hardware, privileged
host state, published services, or wall-clock performance thresholds. If a test
must depend on those things, mark it so it is not pulled into the fast path by
accident.

Preferred locations:

- `tests/core/`: PyRogue tree, node, device, variable, command, block, YAML,
  logging, and concurrency semantics that can run on local emulators.
- `tests/interfaces/`: Python interface wrappers, client/server helpers, GUI
  smoke paths, ZMQ lifecycle tests, and simulation interfaces.
- `tests/protocols/`: protocol parsing, framing, emulation, and deterministic
  protocol behavior.
- `tests/integration/`: real TCP/ZMQ/stream/memory transport paths and
  cross-component behavior.
- `tests/perf/`: benchmark-style checks and perf result export.

Run focused Python tests with `python -m pytest <path> -q` after building and
sourcing the build environment. The default fast selection is:

```sh
python -m pytest -m "not integration and not epics and not perf" -q
```

## Native C++ Tests

Native tests live under `tests/cpp/` and use doctest. They are opt-in at
configure time with `-DROGUE_BUILD_TESTS=ON`.

Patterns to follow:

- Register each executable with `rogue_add_cpp_test()` in the nearest
  `CMakeLists.txt`.
- Label every test executable with the narrow labels it supports.
- Keep no-Python tests compatible with `-DNO_PYTHON=1 -DSTATIC_LIB=1`.
- Prefer deterministic in-memory fakes such as small local `Slave`
  implementations over real sockets unless the socket behavior is the point.
- Use `REQUIRE` for preconditions that make later checks meaningless, and
  `CHECK` for independent assertions.
- Use `CHECK_THROWS_AS` or explicit error assertions when pinning failure
  contracts.
- Use helpers from `tests/cpp/support/test_helpers.h` for stream frames,
  frame byte reads/writes, pools, and bounded asynchronous waits.
- Add platform guards for tests that depend on platform-specific facilities
  such as glibc allocation counters.
- Do not add source-audit tests that read production source files and assert on
  implementation text. Prefer behavioral tests, focused fakes, sanitizer runs,
  or narrowly scoped static-analysis tooling outside the unit test suite.

Label intent:

- `cpp`: added automatically to all native tests.
- `cpp-core`: deterministic native regression subset.
- `no-python`: runnable in the small static no-Python build.
- `requires-python`: requires a Python-enabled Rogue build.
- `smoke`: public API smoke coverage.

Run all Python-enabled native tests from a Python-enabled build:

```sh
ctest --test-dir build --output-on-failure -L cpp
```

Run the no-Python native subset after reconfiguring with `-DNO_PYTHON=1`:

```sh
ctest --test-dir build --output-on-failure -L no-python
```

## Build Environments

The repository uses build outputs from `build/` for both Python and C++ test
execution. Most local commands should:

1. Configure and build Rogue.
2. Install into the selected local or conda runtime.
3. Source `build/setup_rogue.sh`.
4. Run pytest or ctest from that same build tree.

The VS Code tasks assume a `rogue_build` conda environment and provide the
common local entry points:

- `Code: Build Only`
- `Code: Build + Install`
- `Tests: Fast Python`
- `Tests: Core`
- `Tests: Interfaces`
- `Tests: Integration`
- `Tests: Perf`
- `Tests: Full Python Coverage`

GitHub Actions in `.github/workflows/rogue_ci.yml` exercises a broader matrix:

- Linux full build: checks whitespace/tabs, runs linters, builds with
  `-DROGUE_BUILD_TESTS=ON`, runs `ctest -L cpp`, then runs pytest with coverage
  and `-m "not perf"`.
- Linux small build: builds with
  `-DROGUE_BUILD_TESTS=ON -DNO_PYTHON=1 -DSTATIC_LIB=1`, then runs
  `ctest -L no-python`.
- macOS arm64 build: builds a Python-enabled conda install, checks imports,
  runs `ctest -L cpp`, then runs pytest with `-m "not perf"`.
- Performance job: builds Rogue, runs `tests/perf`, exports JSON metrics, and
  publishes a perf summary artifact.

Before pushing, choose the smallest local command that covers the change, then
consider the matching CI job. For changes in shared C++ internals, run both a
Python-enabled `ctest -L cpp` path and the no-Python subset when the changed
code is compiled into the small build.

## Agent Checklist

When adding production code, an AI agent should do this before editing tests:

1. Identify whether the changed behavior is Python-only, C++-only, or crosses
   the Python/C++ boundary.
2. Locate nearby tests in the same subsystem and copy their style, fixtures,
   labels, and naming conventions.
3. Decide whether the new coverage belongs in a fast deterministic test,
   integration test, perf test, Python-enabled native test, no-Python native
   test, or a small combination of those.
4. Confirm the relevant local command from this guide, `tests/README.md`,
   `tests/cpp/README.md`, `.vscode/tasks.json`, or `rogue_ci.yml`.
5. Add tests that fail for the old behavior when that is practical.
6. Run the narrow test first, then expand to the nearest suite or label that CI
   will use for the changed surface.

Do not stage or commit test changes unless the user explicitly asks for that.
