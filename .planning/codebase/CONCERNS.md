# Codebase Concerns

**Analysis Date:** 2026-03-24

## Tech Debt

**C++ Standard Conflict in CMakeLists.txt:**
- Issue: `CMakeLists.txt` line 53 sets `-std=c++11` in `CMAKE_CXX_FLAGS`, while line 56 sets `CMAKE_CXX_STANDARD 14`. The flag-based setting takes precedence over the CMake variable in many toolchains, meaning the project may compile as C++11 even though C++14 is intended. Both standards are outdated; C++17 is widely available and would enable `std::optional`, `std::string_view`, structured bindings, and other simplifications.
- Files: `CMakeLists.txt` (lines 53, 56)
- Impact: Prevents use of C++14/17 features. The `-Wno-deprecated` flag also silences useful deprecation warnings.
- Fix approach: Remove the `-std=c++11` flag from `CMAKE_CXX_FLAGS`. Update `CMAKE_CXX_STANDARD` to 17 after verifying all dependencies (Boost.Python, ZeroMQ, bzip2) support it. Remove `-Wno-deprecated` or scope it to specific third-party headers.

**Manual Memory Management (malloc/free) in C++:**
- Issue: Core classes use raw `malloc`/`free` for buffer allocation instead of RAII containers or smart pointers. This pattern is error-prone and has already produced at least one bug (see Pool destructor below).
- Files: `src/rogue/interfaces/memory/Block.cpp` (lines 104-114, 122-125, 658, 715), `src/rogue/interfaces/memory/Variable.cpp` (lines 180-217, 445-447), `src/rogue/interfaces/memory/Emulate.cpp` (lines 59, 90), `src/rogue/interfaces/stream/Pool.cpp` (lines 53, 96, 161), `src/rogue/utilities/Prbs.cpp` (lines 81, 103, 147, 149)
- Impact: Risk of memory leaks if exceptions are thrown between allocation and deallocation. Potential double-free or use-after-free bugs. Makes code harder to reason about ownership.
- Fix approach: Replace `malloc`/`free` with `std::vector<uint8_t>` or `std::unique_ptr<uint8_t[]>` where possible. For `Pool` and `Block`, performance-sensitive paths may justify raw allocation, but should wrap in RAII classes. The `Variable` destructor pattern (check NULL then free) is a candidate for `std::unique_ptr`.

**Wildcard Star Imports in pyrogue `__init__.py`:**
- Issue: All submodule exports are imported via `from pyrogue._Foo import *` without any `__all__` definitions in the submodules. This pollutes the `pyrogue` namespace with every public symbol from every submodule.
- Files: `python/pyrogue/__init__.py` (lines 18-30), all `python/pyrogue/_*.py` files (no `__all__` defined)
- Impact: Namespace pollution makes it difficult to determine which symbols are part of the public API. IDE autocomplete becomes noisy. Risk of accidental name collisions between submodules.
- Fix approach: Add `__all__` lists to each `_*.py` submodule, or switch to explicit named imports in `__init__.py`.

**Python 3.6 Minimum Version:**
- Issue: `python/pyrogue/__init__.py` line 14 checks for Python 3.6 minimum, but the codebase uses type hints like `X | Y` union syntax (PEP 604, Python 3.10+) and `from __future__ import annotations` throughout. The CI runs Python 3.12. The stated minimum is misleading.
- Files: `python/pyrogue/__init__.py` (line 14)
- Impact: Misleads users about compatibility. Code will not actually run on Python 3.6-3.9.
- Fix approach: Update the minimum version check to Python 3.10 or higher to match the actual feature usage.

**`eval()` Usage for Dynamic Code Generation:**
- Issue: `eval()` is used to construct lambda wrappers dynamically from string interpolation. While the inputs are derived from function introspection (not user input), this pattern is fragile and hard to debug.
- Files: `python/pyrogue/_HelperFunctions.py` (lines 433, 450), `python/pyrogue/_Node.py` (line 982), `python/pyrogue/_Variable.py` (line 973)
- Impact: Difficult to debug when the generated lambda has issues. Static analysis tools cannot inspect the generated code. Minor injection risk if callback argument names contain unexpected characters.
- Fix approach: Replace `eval()` lambda generation with `functools.partial` or explicit closure construction. For the slice evaluation in `_Node.py` and `_Variable.py`, use `slice()` built-in with explicit parsing.

**Commented-Out Code:**
- Issue: Several files contain commented-out debug print statements, disabled commands, and dead code that clutters the codebase.
- Files: `python/pyrogue/_Root.py` (lines 72, 361-365), `python/pyrogue/_Device.py` (line 84), `tests/test_memory.py` (lines 17-20)
- Impact: Minor clutter. Could confuse contributors about intended behavior.
- Fix approach: Remove commented-out code. Use logging at DEBUG level instead of commented print statements.

## Known Bugs

**Pool Destructor Infinite Loop:**
- Symptoms: The `Pool::~Pool()` destructor enters an infinite loop and hangs the process on cleanup.
- Files: `src/rogue/interfaces/stream/Pool.cpp` (lines 51-55)
- Trigger: Any normal teardown of a Pool object that has cached buffers in `dataQ_`. The while loop calls `free(dataQ_.front())` but never calls `dataQ_.pop()`, so the queue never becomes empty.
- Workaround: In practice, Pool objects may persist for the lifetime of the process so this may rarely trigger, but it will hang on clean shutdown.
- Fix: Add `dataQ_.pop()` after the `free(dataQ_.front())` call inside the while loop.

**Exception Caught by Value in Block.cpp:**
- Symptoms: Exception slicing when catching `rogue::GeneralError` by value instead of by reference.
- Files: `src/rogue/interfaces/memory/Block.cpp` (lines 292, 332)
- Trigger: Any transaction retry that catches a `GeneralError`. If a subclass of `GeneralError` is thrown, the subclass data is sliced off.
- Workaround: None needed currently if no `GeneralError` subclasses exist, but the pattern is incorrect.
- Fix: Change `catch (rogue::GeneralError err)` to `catch (const rogue::GeneralError& err)` at both locations.

**EPICS V4 Module Has Unresolved TODO:**
- Symptoms: The module header states "TODO: Not clear on to force a read on get" indicating incomplete behavior for EPICS get operations.
- Files: `python/pyrogue/protocols/epicsV4.py` (lines 6-7)
- Trigger: EPICS get operations may not trigger hardware reads when they should.
- Workaround: Not documented.

## Security Considerations

**`eval()` for Dynamic Lambda Construction:**
- Risk: While `eval()` inputs come from introspected function argument names (not user input), if a custom Device or Variable ever had argument names containing malicious content, code injection would be possible. The `_Node.py` and `_Variable.py` uses pass user-provided slice strings through `eval()` (e.g., `eval(f'tmpList[{keys[0]}]')` where `keys[0]` comes from node path parsing).
- Files: `python/pyrogue/_HelperFunctions.py` (lines 433, 450), `python/pyrogue/_Node.py` (line 982), `python/pyrogue/_Variable.py` (line 973)
- Current mitigation: The inputs are typically constrained to valid Python identifiers or slice syntax. The docstring in `_HelperFunctions.py` notes that `callArgs` "should contain trusted identifier strings."
- Recommendations: Replace `eval()` with `slice()` parsing for index/slice expressions. Use explicit closure construction instead of string-based lambda generation.

**ZMQ Server Without Authentication:**
- Risk: The `ZmqServer` binds to a network port and accepts arbitrary requests. There is no authentication or authorization mechanism for incoming ZMQ connections.
- Files: `src/rogue/interfaces/ZmqServer.cpp`, `python/pyrogue/interfaces/_ZmqServer.py`
- Current mitigation: Typically deployed on internal lab networks behind firewalls. The default bind address can be configured.
- Recommendations: For deployments outside trusted networks, add authentication (ZMQ CURVE or application-level tokens). Document the security model clearly.

## Performance Bottlenecks

**Busy-Wait Spin Loops with `usleep(10)`:**
- Problem: Multiple protocol controllers use `usleep(10)` in tight loops to wait for conditions, consuming CPU time unnecessarily.
- Files: `src/rogue/protocols/rssi/Controller.cpp` (line 399), `src/rogue/protocols/packetizer/ControllerV1.cpp` (line 205), `src/rogue/protocols/packetizer/ControllerV2.cpp` (line 278), `src/rogue/interfaces/api/Bsp.cpp` (line 55)
- Cause: Polling approach instead of event-driven signaling. The RSSI controller waits for `txListCount_ < curMaxBuffers_` in a spin loop.
- Improvement path: Use condition variables (`std::condition_variable`) with `wait()` / `notify_one()` instead of busy-wait loops. The `Bsp.cpp` startup wait should use a callback or event mechanism instead of `usleep(10)` polling.

**JSON Serialization of System Log on Every Log Entry:**
- Problem: Every log record triggers JSON parsing and serialization of the entire system log list. With `_maxLog` entries, this grows linearly.
- Files: `python/pyrogue/_Root.py` (lines 119-146, `RootLogHandler.emit`)
- Cause: The entire system log is stored as a JSON string in a `LocalVariable`, requiring full deserialization and re-serialization on each new log entry. A recent fix (PR #1153) addressed a memory leak in this path, but the O(n) serialization per log entry remains.
- Improvement path: Store the log as a native Python list internally and only serialize to JSON on demand (e.g., when the variable value is read by a GUI or remote client).

**`gettimeofday()` Usage Instead of Monotonic Clock:**
- Problem: Extensive use of `gettimeofday()` for timing in protocol controllers. This call is not monotonic -- NTP adjustments, daylight saving changes, or manual clock changes can cause incorrect timeout behavior.
- Files: `src/rogue/protocols/rssi/Controller.cpp` (14 calls), `src/rogue/protocols/packetizer/ControllerV1.cpp`, `src/rogue/protocols/packetizer/ControllerV2.cpp`, `src/rogue/interfaces/memory/Transaction.cpp`, `src/rogue/utilities/fileio/StreamWriter.cpp`, `src/rogue/utilities/fileio/StreamWriterChannel.cpp`, `src/rogue/interfaces/stream/RateDrop.cpp`
- Cause: Legacy code pattern. `gettimeofday()` was common before `clock_gettime(CLOCK_MONOTONIC)` became widely available.
- Improvement path: Replace all timing uses with `std::chrono::steady_clock` (C++11) or `clock_gettime(CLOCK_MONOTONIC)`.

## Fragile Areas

**Block.cpp -- Memory Transaction Engine (2088 lines):**
- Files: `src/rogue/interfaces/memory/Block.cpp` (2088 lines), `include/rogue/interfaces/memory/Block.h` (908 lines)
- Why fragile: This is the largest file in the codebase and handles the critical path for all hardware register access. It manages raw byte buffers with manual `malloc`/`free`, complex bit-level operations (`copyBits`, `reverseBytes`), stale tracking across multiple variables, and retry logic with exception handling. The class mixes concerns: buffer management, transaction orchestration, variable indexing, bit manipulation, and Python binding.
- Safe modification: Any change should be accompanied by tests in `tests/test_memory.py`, `tests/test_list_memory.py`, and `tests/test_block_overlap.py`. Run the full test suite; regressions in Block often cascade through the entire variable system.
- Test coverage: Moderate -- `test_memory.py` (200 lines) and `test_list_memory.py` (479 lines) cover basic read/write scenarios, but edge cases in bit manipulation, stale tracking, and retry logic have limited coverage.

**GIL Management Across C++/Python Boundary:**
- Files: `src/rogue/GilRelease.cpp`, `src/rogue/ScopedGil.cpp`, and ~55 source files using `GilRelease` or `ScopedGil`
- Why fragile: Every C++ function that calls into Python or is called from Python must correctly manage the GIL. Missing a GIL release before blocking operations causes Python thread starvation. Missing a GIL acquire before Python API calls causes segfaults. The `GilRelease` constructor checks `Py_IsInitialized()` and `PyGILState_Check()` which adds conditional complexity.
- Safe modification: Always use the RAII wrappers (`GilRelease` for releasing, `ScopedGil` for acquiring). Never mix raw `PyEval_SaveThread`/`PyEval_RestoreThread` with the wrappers. Test with multi-threaded Python clients.
- Test coverage: No dedicated GIL-handling tests. Failures manifest as deadlocks or segfaults.

**RSSI Controller State Machine (984 lines):**
- Files: `src/rogue/protocols/rssi/Controller.cpp`, `include/rogue/protocols/rssi/Controller.h`
- Why fragile: Implements a reliable transport protocol with complex state machine logic (StClosed, StWaitSyn, StSendSeqAck, StOpen, etc.), retransmission tracking, sequence number management, and bidirectional flow control. Uses multiple mutexes and condition variables with busy-wait fallbacks. Recent commits addressed race conditions (`udp-rssi-startup-race`).
- Safe modification: Changes require testing with `tests/test_udpPacketizer.py` and ideally integration testing with actual RSSI firmware. Timing-sensitive changes are especially risky.
- Test coverage: `test_udpPacketizer.py` (169 lines) provides basic integration coverage but does not test error recovery, retransmission, or connection state transitions.

**Root._updateWorker and Update Tracking:**
- Files: `python/pyrogue/_Root.py` (lines 37-88, 511-540, 1111-1178)
- Why fragile: The `UpdateTracker` mechanism uses per-thread dictionaries keyed by `threading.get_ident()`, with a fallback exception-based initialization pattern (`try/except Exception` to check if tracker exists). Thread ID reuse could theoretically cause stale tracker references. The update queue worker uses `queue.Queue.get()` with `None` as a sentinel, which works but is fragile if other code accidentally puts `None` into the queue.
- Safe modification: Test with `tests/test_root.py` and verify update listeners fire correctly. Add logging around the update path when debugging.
- Test coverage: `test_root.py` is only 26 lines and does not test the update worker, variable listeners, or update grouping.

## Scaling Limits

**32-bit Allocation Counters in Pool:**
- Current capacity: `allocBytes_` and `allocCount_` are `uint32_t`, limiting tracking to ~4GB total allocated and ~4 billion buffers.
- Limit: Long-running high-rate data acquisition systems could overflow these counters.
- Files: `include/rogue/interfaces/stream/Pool.h` (lines 76-82), `src/rogue/interfaces/stream/Pool.cpp`
- Scaling path: Change to `uint64_t` or `std::atomic<uint64_t>` for long-running deployments.

**SystemLog JSON String Growth:**
- Current capacity: Bounded by `_maxLog` (default not explicitly set in constructor; managed by truncation in emit). Each log entry is JSON-serialized.
- Limit: High-frequency logging causes O(n) serialization on each entry. With `_maxLog` of 1000+ entries, this becomes a measurable overhead.
- Files: `python/pyrogue/_Root.py` (lines 119-146)
- Scaling path: Use a deque or ring buffer internally, serialize only on read.

## Dependencies at Risk

**Boost.Python:**
- Risk: Boost.Python is in maintenance mode; the Python community has moved to `pybind11` which is header-only, has better template support, and produces smaller binaries. Boost.Python requires matching the Boost version with the Python version, which causes build friction (see the 5-candidate search loop in `CMakeLists.txt` lines 93-108).
- Impact: Build complexity, slower compilation, larger binary size. The `CMakeLists.txt` has an elaborate fallback search for the correct Boost.Python component name.
- Files: `CMakeLists.txt` (lines 64-118), all `src/rogue/**/*.cpp` files
- Migration plan: Migrating to pybind11 is a major effort but would simplify builds significantly. The current Boost.Python binding patterns (class wrappers, `bp::class_`, `bp::init<>`, `bp::extract<>`) have near-direct equivalents in pybind11.

**ZeroMQ CMake Discovery:**
- Risk: ZeroMQ CMake package detection is unreliable, requiring a manual fallback in `CMakeLists.txt` (lines 130-159) that searches `LD_LIBRARY_PATH` and `DYLD_LIBRARY_PATH`.
- Impact: Build failures on systems where ZeroMQ is installed but its cmake config is missing.
- Files: `CMakeLists.txt` (lines 127-159)
- Migration plan: Use `pkg-config` as a more reliable fallback, or pin to a ZeroMQ version that ships cmake configs.

## Missing Critical Features

**No C++ Test Coverage Measurement:**
- Problem: The CI runs `python -m pytest --cov` which only measures Python code coverage. The C++ code (18,974 lines across 78 source files) has no coverage measurement.
- Blocks: Cannot identify untested C++ code paths, especially in critical areas like `Block.cpp`, `Controller.cpp`, and GIL management.
- Files: `.github/workflows/rogue_ci.yml` (lines 72-74)

**No Thread Sanitizer or Address Sanitizer in CI:**
- Problem: Given the heavy use of threading (20+ thread launches across Python code, C++ threads in protocols and ZMQ), there is no TSan or ASan build in CI to catch data races and memory errors.
- Blocks: Race conditions and memory errors may go undetected until they manifest in production. Recent commits show this is an active concern (`udp-rssi-startup-race`, `pre-release-logging-mem-leak-fix`).
- Files: `.github/workflows/rogue_ci.yml`, `CMakeLists.txt`

## Test Coverage Gaps

**Root Lifecycle and Update Workers:**
- What's not tested: Variable listener callbacks, update grouping (`updateGroup` context manager), heartbeat worker, poll enable/disable interactions, log handler memory management.
- Files: `tests/test_root.py` (26 lines -- only tests basic start/stop)
- Risk: The recent logging memory leak fix (PR #1153) and system log record filtering (commit ec209400b) indicate active bugs in this area.
- Priority: High

**RSSI Protocol State Machine:**
- What's not tested: Connection establishment/teardown sequences, retransmission logic, flow control back-pressure, out-of-order packet handling, connection ID negotiation.
- Files: `tests/test_udpPacketizer.py` (169 lines -- basic data transfer only)
- Risk: Race conditions have been found and fixed (commit 87ee6ffaa). The state machine is complex (984 lines) with 5+ states and timing-dependent transitions.
- Priority: High

**GIL Management:**
- What's not tested: No tests exercise concurrent Python and C++ threads to validate GIL release/acquire correctness. Deadlocks and segfaults from GIL misuse are only caught by integration testing.
- Files: `src/rogue/GilRelease.cpp`, `src/rogue/ScopedGil.cpp`
- Risk: GIL-related bugs cause hard-to-reproduce crashes. The complexity of having 182 GIL management calls across 55 source files means any new code path is at risk.
- Priority: Medium

**ZMQ Server/Client:**
- What's not tested: Connection loss handling, message serialization edge cases, concurrent request handling in `ZmqServer::runThread()`.
- Files: `src/rogue/interfaces/ZmqServer.cpp`, `src/rogue/interfaces/ZmqClient.cpp`
- Risk: ZMQ errors in `runThread()` throw `GeneralError` but are not caught, which could crash the server thread. The `PyBuffer_Release` call at line 305 could leak if `zmq_sendmsg` fails.
- Priority: Medium

**FileIO Stream Writer/Reader:**
- What's not tested: File rotation, concurrent write access, corrupted file recovery, large file handling beyond buffer size limits.
- Files: `tests/test_file.py` (108 lines -- basic read/write only)
- Risk: Recent bugfixes in `bugfix/fileio-readers` branch (commits 5fcfaca75, 582133155) indicate active issues in this area.
- Priority: Medium

**Bsp (Board Support Package) C++ API:**
- What's not tested: The `Bsp.cpp` API catches all exceptions with `catch(...)` and re-throws as `GeneralError`, losing the original exception context. The C++ API test (`tests/api_test/src/api_test.cpp`) exists but error paths are not tested.
- Files: `src/rogue/interfaces/api/Bsp.cpp` (11 `catch(...)` blocks), `tests/api_test/src/api_test.cpp`
- Risk: Original exception information is lost, making debugging difficult for C++ API users. The `Bsp::get()` and `Bsp::readGet()` methods use the wrong error string (`"Bsp::set"` instead of `"Bsp::get"` at lines 176, 185).
- Priority: Low

---

*Concerns audit: 2026-03-24*
