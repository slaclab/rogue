# Branch Status

This document is a handoff summary for the long-running test/coverage branch.
It now covers both the Python test suite reorganization and the in-tree native
C++ test suite added on top of that work.

## Current Test Layout

The test suite was reorganized by behavior and execution style:

- `tests/core/`: deterministic PyRogue tree/runtime behavior
- `tests/interfaces/`: client/server wrappers and interface helpers
- `tests/fileio/`: file and stream reader/writer behavior
- `tests/protocols/`: protocol-specific deterministic tests
- `tests/integration/`: real transport, socket, and environment-dependent tests
- `tests/perf/`: soak, throughput, and benchmark-style tests
- `tests/utilities/`: helper and exporter modules
- `tests/cpp/`: native C++ unit and smoke tests driven by `ctest`

## High-Level Outcomes

The branch focused on four things:

1. Increase deterministic coverage of core PyRogue behavior.
2. Reorganize the test suite so file names and directories match behavior.
3. Add more real end-to-end interface/integration coverage while reducing
   dependence on fixed local ports.
4. Add an in-tree native C++ regression suite for low-level Rogue core
   behaviors.

## Coverage / Validation Snapshot

Most recent known results from the branch work:

- Fast deterministic suite:
  - `pytest -m "not integration and not epics and not perf" -q`
  - result: `143 passed, 16 deselected`
- Full unsandboxed Python suite:
  - `python -m pytest --cov`
  - result: `159 passed`
  - total Python coverage: `56%`
- Python-enabled native C++ smoke subset:
  - `ctest --test-dir build --output-on-failure -L requires-python`
  - result: passed in a Python-enabled build
- Deterministic native C++ core subset:
  - `ctest --test-dir build --output-on-failure -L cpp-core`
  - result: passed in a dedicated native test build
- Deterministic no-Python native subset:
  - `ctest --test-dir build --output-on-failure -L no-python`
  - result: passed in a `-DNO_PYTHON=1` build

Selected module coverage from the last full run:

- `python/pyrogue/_Root.py`: `91%`
- `python/pyrogue/_Device.py`: `88%`
- `python/pyrogue/_Node.py`: `88%`
- `python/pyrogue/_Variable.py`: `83%`
- `python/pyrogue/_Command.py`: `90%`
- `python/pyrogue/_Process.py`: `98%`
- `python/pyrogue/interfaces/_SimpleClient.py`: `100%`
- `python/pyrogue/interfaces/_Virtual.py`: `86%`
- `python/pyrogue/interfaces/_ZmqServer.py`: `97%`
- `python/pyrogue/utilities/cpsw.py`: `88%`

## Important Structural Changes Already Done

### Test reorganization

- Old legacy files were moved into the new layout.
- Misleading integration names were cleaned up, for example:
  - `test_memory_transport_integration.py`
  - `test_remote_enum_integration.py`
  - `test_remote_list_variable_integration.py`
  - `test_stream_bridge_integration.py`
  - `test_udp_packetizer_integration.py`
- Performance/soak-style tests were split into `tests/perf/`.

### Native C++ test suite

- `ROGUE_BUILD_TESTS` was added as a top-level CMake option, default `ON`.
- `enable_testing()` and a `tests/cpp` subtree were added to the main build.
- A shared native test support target now provides the doctest main and common
  helpers for individual test executables.
- Common CTest labels were added:
  - `cpp`
  - `cpp-core`
  - `no-python`
  - `requires-python`
  - `smoke`
- The current deterministic native test files are:
  - `tests/cpp/core/test_version.cpp`
  - `tests/cpp/memory/test_memory_bits.cpp`
  - `tests/cpp/memory/test_transaction_block.cpp`
  - `tests/cpp/memory/test_variable.cpp`
  - `tests/cpp/stream/test_frame_pool.cpp`
  - `tests/cpp/stream/test_iterator.cpp`
  - `tests/cpp/stream/test_fifo_filter_rate_drop.cpp`
- The current Python-enabled smoke test file is:
  - `tests/cpp/smoke/test_api_smoke.cpp`

### Shared test infrastructure

- `tests/conftest.py` now provides:
  - `MemoryRoot`
  - `wait_until`
  - log suppression helpers for normal test runs
  - `_find_free_port_block(...)`
  - `free_zmq_port`
  - `free_tcp_port`

### New high-value end-to-end interface coverage

- `tests/interfaces/test_interfaces_virtual_integration.py`
  - live `VirtualClient` over `ZmqServer`
  - includes `NoServe` remote-tree visibility behavior
- `tests/interfaces/test_interfaces_simple_client_integration.py`
  - live `SimpleClient` over `ZmqServer`

### Dynamic port allocation

Several socket-backed tests were converted away from fixed ports:

- `tests/interfaces/test_interfaces_virtual_integration.py`
- `tests/interfaces/test_interfaces_simple_client_integration.py`
- `tests/integration/test_memory_transport_integration.py`
- `tests/integration/test_remote_enum_integration.py`
- `tests/integration/test_stream_bridge_integration.py`

`tests/integration/test_udp_packetizer_integration.py` already used dynamic
binding through the Rogue API and did not need to change.

## Notable Product / Test Fixes Made On This Branch

This branch found and fixed a number of real bugs while expanding coverage.
Examples include:

- `_Model.py`
  - `Int.fromBytes()` returned `None`
  - `Int.fromString()` mishandled sign extension for non-byte-aligned widths
- `_Block.py`
  - `LocalBlock` in-place operators passed `None` where a real variable was
    required
- `_Variable.py`
  - indexed `_setDict()` bug for scalar array indices
  - indexed `setDisp()` bug for 0-D ndarray values
  - `VariableWaitClass.get_values()` key mismatch
  - missing documented `VariableValue.updated` field
  - YAML slice scalar broadcasting fix
- `_Process.py`
  - `__call__()` argument-variable bug
  - progress overruns above 100%
  - progress clamping/zero-total handling
- `utilities/cpsw.py`
  - malformed child-device output
  - overwritten file prologue
- `interfaces/_SqlLogging.py`
  - syslog JSON decoding used the wrapper object instead of the string payload
- `utilities/fileio/_FileReader.py`
  - config/status parsing used unsupported bare `yaml.load(...)`
- `src/rogue/interfaces/ZmqClient.cpp`
  - raw timeout `printf` replaced by a debug log call
- `src/rogue/interfaces/memory/Master.cpp`
  - zero-length `copyBits`, `setBits`, and `anyBits` requests incorrectly ran
    a loop iteration instead of behaving as no-ops
- `src/rogue/interfaces/stream/Pool.cpp`
  - the destructor repeatedly freed the same queue front without advancing,
    which the new frame/pool tests exposed

## Recent CI / Test Stability Notes

- The SQL logging test needed hardening because CI sometimes raced teardown
  before the listener-driven syslog row landed in SQLite.
  - `tests/interfaces/test_interfaces_sql_logging.py` now waits for the row.
- This Rogue build does not support `ZmqServer(..., port=0)` auto-bind in the
  integration tests used here.
  - The tests now use caller-selected free ports instead.
- Local shell runs can fail with:
  - `rogue.GeneralError: Invalid compiled version string`
  when the Python source overlay and compiled Rogue install are out of sync.
  Rebuild or reinstall before trusting local results.
- On macOS, local `ctest` runs can also pick up an installed Rogue library from
  `lib/` instead of the fresh build tree unless the runtime library path points
  at `build/`. Keep that in mind before treating local native failures as real
  regressions.

## Things That Are Still Intentionally Low Coverage

These areas were not the focus of the branch and still show low or zero
coverage:

- `python/pyrogue/examples/*`
- `python/pyrogue/pydm/*`
- `python/pyrogue/protocols/gpib.py`
- `python/pyrogue/utilities/hls/_RegInterfParser.py`
- `python/pyrogue/utilities/prbs.py`
- `python/pyrogue/interfaces/stream/*`
- socket-backed native transport coverage under `tests/cpp/`
- native protocol-transform coverage beyond the basic API smoke path

That is expected for this branch unless the next work item explicitly targets
those modules.
