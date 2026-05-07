# Native C++ Test Suite

The native C++ tests live under `tests/cpp/` and are organized by behavior:

- `core/`: deterministic native helper and utility coverage
- `memory/`: memory bit helpers plus transaction/block and variable behavior
- `stream/`: frame, pool, iterator, FIFO, filter, and rate-drop behavior
- `protocols/`: protocol helpers, packetizer coverage, and XVC smoke coverage
- `smoke/`: higher-level API smoke coverage that requires Python support
- `support/`: shared test main and helper utilities
- `vendor/`: vendored upstream single-header test framework and provenance notes

For test selection and authoring guidance across both pytest and native C++,
see `../METHODOLOGY.md`.

Current scope:

- Fast deterministic native coverage is centered on low-level core, memory,
  stream, and packetizer behavior that does not require sockets or external
  services.
- The Python-enabled subset contains public API and XVC smoke tests.
- Socket-backed, transport-backed, and perf-style native tests remain deferred
  to later labeled expansions.

Labels:

- `cpp`: all native C++ tests
- `cpp-core`: fast deterministic native regression subset
- `no-python`: tests that also run in `-DNO_PYTHON=1` builds
- `requires-python`: tests that depend on Python-enabled Rogue builds
- `smoke`: public API smoke coverage

Common commands:

- Native C++ tests are opt-in for manual builds. Enable them with
  `-DROGUE_BUILD_TESTS=ON`.
- Configure/build with native tests in the standard repo-local `build/`
  directory:
  - `cmake -S . -B build -DROGUE_INSTALL=local -DROGUE_BUILD_TESTS=ON`
  - `cmake --build build -j$(nproc)`
  - `cmake --build build --target install`
- Run all Python-enabled native tests from that same `build/` tree:
  - `source build/setup_rogue.sh`
  - `ctest --test-dir build --output-on-failure -L cpp`
- Run the Python-enabled smoke subset from the same `build/` tree:
  - `source build/setup_rogue.sh`
  - `ctest --test-dir build --output-on-failure -L requires-python`
- Reconfigure that same `build/` tree for a small no-Python build when
  needed:
  - `cmake -S . -B build -DROGUE_INSTALL=local -DROGUE_BUILD_TESTS=ON -DNO_PYTHON=1 -DSTATIC_LIB=1`
  - `cmake --build build -j$(nproc)`
  - `cmake --build build --target install`
- Run the deterministic native subset in a no-Python build:
  - `source build/setup_rogue.sh`
  - `ctest --test-dir build --output-on-failure -L cpp-core`
- Run the no-Python native subset:
  - `source build/setup_rogue.sh`
  - `ctest --test-dir build --output-on-failure -L no-python`

Current deterministic test files:

- `core/test_atomic_thread_flags.cpp`
- `core/test_ctor_catch_thread_cleanup.cpp`
- `core/test_version.cpp`
- `memory/test_memory_bits.cpp`
- `memory/test_transaction_block.cpp`
- `memory/test_variable.cpp`
- `protocols/packetizer/test_crc.cpp`
- `protocols/packetizer/test_partial_construction.cpp`
- `stream/test_frame_pool.cpp`
- `stream/test_iterator.cpp`
- `stream/test_fifo_filter_rate_drop.cpp`

Current Python-enabled smoke test files:

- `smoke/test_api_smoke.cpp`
- `protocols/xilinx/test_xvc_smoke.cpp`
