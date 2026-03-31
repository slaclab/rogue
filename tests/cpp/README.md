# Native C++ Test Suite

The native C++ tests live under `tests/cpp/` and are organized by behavior:

- `core/`: deterministic native helper and utility coverage
- `memory/`: deterministic memory-layer helpers
- `stream/`: frame, pool, and iterator behavior
- `smoke/`: higher-level API smoke coverage that requires Python support
- `support/`: shared test main and helper utilities
- `vendor/`: vendored single-header test harness

Labels:

- `cpp`: all native C++ tests
- `cpp-core`: fast deterministic native regression subset
- `no-python`: tests that also run in `-DNO_PYTHON=1` builds
- `requires-python`: tests that depend on Python-enabled Rogue builds
- `smoke`: public API smoke coverage

Common commands:

- Configure/build with native tests in the standard repo-local `build/`
  directory:
  - `cmake -S . -B build -DROGUE_INSTALL=local -DROGUE_BUILD_TESTS=ON`
  - `cmake --build build -j$(nproc)`
- Run the Python-enabled smoke subset from the same `build/` tree:
  - `source build/setup_rogue.sh`
  - `ctest --test-dir build --output-on-failure -L requires-python`
- Reconfigure that same `build/` tree for a small no-Python build when
  needed:
  - `cmake -S . -B build -DROGUE_INSTALL=local -DROGUE_BUILD_TESTS=ON -DNO_PYTHON=1 -DSTATIC_LIB=1`
  - `cmake --build build -j$(nproc)`
- Run the deterministic native subset in a no-Python build:
  - `source build/setup_rogue.sh`
  - `ctest --test-dir build --output-on-failure -L cpp-core`
- Run the no-Python native subset:
  - `source build/setup_rogue.sh`
  - `ctest --test-dir build --output-on-failure -L no-python`
