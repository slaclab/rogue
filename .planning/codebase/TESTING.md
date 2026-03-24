# Testing Patterns

**Analysis Date:** 2026-03-24

## Test Framework

**Runner:**
- pytest >= 3.6
- Config: No `pytest.ini` or `pyproject.toml` test config; pytest auto-discovers `tests/test_*.py`

**Assertion Library:**
- Built-in `assert` statements (newer tests)
- `raise AssertionError(...)` pattern (older/majority of tests -- note the consistent historical spelling)

**Coverage:**
- coverage.py with config at `.coveragerc`
- pytest-cov plugin for integrated coverage
- codecov for reporting

**Run Commands:**
```bash
source setup_rogue.sh             # Required: set up rogue environment
python -m pytest --cov             # Run all tests with coverage
python -m pytest tests/test_memory.py  # Run a single test file
python -m pytest -v                # Verbose output
coverage report -m                 # View coverage report after test run
```

## Test File Organization

**Location:**
- All Python tests in `tests/` directory at project root (NOT co-located with source)
- One C++ API test in `tests/api_test/src/api_test.cpp` (built separately with its own CMake)

**Naming:**
- `test_<feature>.py` for Python test files
- Test functions named `test_<description>()` for pytest auto-discovery

**Structure:**
```
tests/
    .gitignore              # Ignores generated *.yml files
    test_block_overlap.py   # Block overlap/register tests
    test_config_in.yml      # Test fixture YAML config
    test_enum.py            # Enum variable tests
    test_epics.py           # EPICS integration tests
    test_fifo.py            # FIFO stream tests
    test_file.py            # File I/O tests
    test_hub.py             # Hub/virtual address space tests
    test_int.py             # Signed integer variable tests
    test_list_memory.py     # List/array variable tests
    test_loadsave.py        # Config load/save tests
    test_localcommand.py    # Local command tests
    test_localvars.py       # Local variable tests
    test_logging.py         # Logging feedback loop tests
    test_memory.py          # Memory read/write tests
    test_rate.py            # Performance benchmark tests
    test_retry_memory.py    # Memory retry/error handling tests
    test_root.py            # Root lifecycle tests
    test_streamBridge.py    # TCP stream bridge tests
    test_udpPacketizer.py   # UDP/packetizer/RSSI tests
    api_test/               # C++ API test (separate build)
        CMakeLists.txt
        src/api_test.cpp
```

**No conftest.py:** There is no `conftest.py` file. Tests are self-contained.

## Test Structure

**Standard Test Pattern:**
Each test file follows this structure:
1. Define helper `Device` subclass(es) with register definitions
2. Define a `DummyTree` (or similar) `Root` subclass that wires up memory emulation
3. Define `test_<name>()` function(s) that use the root as a context manager

```python
#!/usr/bin/env python3
# [license header]

import pyrogue as pr
import rogue.interfaces.memory

class MyDev(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add(pr.RemoteVariable(
            name         = "RegA",
            offset       =  0x00,
            bitSize      =  32,
            bitOffset    =  0x00,
            base         = pr.UInt,
            mode         = "RW",
        ))

class DummyTree(pr.Root):
    def __init__(self):
        pr.Root.__init__(self,
                         name='dummyTree',
                         description="Dummy tree for testing",
                         timeout=2.0,
                         pollEn=False)

        sim = rogue.interfaces.memory.Emulate(4, 0x1000)
        self.addInterface(sim)

        self.add(MyDev(
            offset     = 0x0,
            memBase    = sim,
        ))

def test_my_feature():
    with DummyTree() as root:
        # Set values
        root.MyDev.RegA.set(42)

        # Read back and verify
        result = root.MyDev.RegA.get()
        if result != 42:
            raise AssertionError(f'Expected 42, got {result}')

if __name__ == "__main__":
    test_my_feature()
```

**Key patterns:**
- Use `with Root() as root:` context manager for setup/teardown
- Memory emulation via `rogue.interfaces.memory.Emulate(minWidth, maxSize)`
- TCP-based memory via `TcpServer`/`TcpClient` pair for more realistic tests
- Each test file is independently runnable via `__main__`
- `pollEn=False` in all test roots to disable background polling

## Test Categories

**Unit-level register tests:**
- `test_memory.py`: RemoteVariable read/write with byte and bit-level access
- `test_int.py`: Signed integer variable encoding
- `test_enum.py`: Enum variable set/get/display
- `test_list_memory.py`: Array/list variable types (UInt, Int, Float, Double, Bool) with numpy
- `test_block_overlap.py`: Overlapping register block access
- `test_localvars.py`: LocalVariable, LinkVariable, type checking, properties
- `test_localcommand.py`: LocalCommand foreground execution timing

**Integration tests:**
- `test_root.py`: Root context manager lifecycle
- `test_loadsave.py`: YAML config save/load round-trip
- `test_hub.py`: Virtual address space hub with SPI-style indirect access
- `test_retry_memory.py`: Memory transaction retry on error
- `test_streamBridge.py`: TCP stream bridge with PRBS verification
- `test_fifo.py`: FIFO stream path with PRBS verification
- `test_udpPacketizer.py`: UDP/packetizer/RSSI protocol stack testing
- `test_epics.py`: EPICS V4 (p4p) PV read/write integration
- `test_file.py`: File writer/reader with compression

**Performance tests:**
- `test_rate.py`: Benchmark set/get operations with cycle-count or wall-clock thresholds

**Logging tests:**
- `test_logging.py`: SystemLog feedback loop prevention, RootLogHandler isolation

## Mocking & Test Doubles

**No mocking framework.** Tests use real rogue C++ objects with memory emulation.

**Memory Emulation (primary test double):**
```python
sim = rogue.interfaces.memory.Emulate(4, 0x1000)  # (minWidth, maxSize)
self.addInterface(sim)
self.add(DeviceUnderTest(
    offset  = 0x0,
    memBase = sim,
))
```

**Custom Memory Slaves:**
For testing complex protocols (hub, retry), tests define custom `rogue.interfaces.memory.Slave` subclasses that emulate hardware behavior:

```python
class LocalEmulate(rogue.interfaces.memory.Slave):
    def __init__(self, *, minWidth=4, maxSize=0xFFFFFFFF):
        rogue.interfaces.memory.Slave.__init__(self, 4, 4)
        self._data = {}

    def _doTransaction(self, transaction):
        address = transaction.address()
        size    = transaction.size()
        type    = transaction.type()

        if type == rogue.interfaces.memory.Write:
            ba = bytearray(size)
            transaction.getData(ba, 0)
            # store data...
            transaction.done()
        elif type == rogue.interfaces.memory.Read:
            # retrieve data...
            transaction.setData(ba, 0)
            transaction.done()
        else:
            transaction.error("Unsupported transaction type")
```

**PRBS Verification (stream tests):**
```python
prbsTx = rogue.utilities.Prbs()
prbsRx = rogue.utilities.Prbs()
prbsTx >> bridge >> prbsRx
prbsRx.checkPayload(True)

for _ in range(FrameCount):
    prbsTx.genFrame(FrameSize)

# Poll for completion
for i in range(300):
    if prbsRx.getRxCount() == FrameCount:
        break
    time.sleep(.1)

if prbsRx.getRxErrors() != 0:
    raise AssertionError('PRBS Frame errors detected!')
```

**Fake/Stub objects (for unit isolation):**
- `test_logging.py` defines `FakeSystemLogVariable` and `FakeLogRoot` classes to test the log handler in isolation without starting a full Root

```python
class FakeSystemLogVariable:
    def __init__(self, name):
        self._log = logging.getLogger(f'pyrogue.Variable.LocalVariable.root.{name}')
        self._value = '[]' if name == 'SystemLog' else ''
        self.calls = 0
        self.overflow = False
        self.lock = contextlib.nullcontext()
        self.path = f'root.{name}'

    def set(self, value):
        self.calls += 1
        if self.calls > 5:
            self.overflow = True
            return
        self._value = value

    def value(self):
        return self._value
```

## Fixtures and Factories

**Test Data:**
- Inline constants at module level: `FrameCount = 10000`, `FrameSize = 10000`
- Inline test values: `test_value=3.14`, `UInt32ListARaw = [int(random.random()*1000) for i in range(32)]`
- YAML fixture file: `tests/test_config_in.yml`

**No pytest fixtures or conftest.py.** Each test file is self-contained with its own device/tree classes.

**Factory pattern:** Each test file defines its own `DummyTree` (or `LocalRoot`, `BlockRoot`) class as a test fixture factory.

## Coverage

**Configuration (`.coveragerc`):**
```ini
[run]
branch = True
source = pyrogue

[report]
exclude_lines =
    if self.debug:
    pragma: no cover
    raise NotImplementedError
    if __name__ == .__main__.:
ignore_errors = True
omit =
    tests/*
```

**Requirements:** No minimum coverage threshold enforced.

**View Coverage:**
```bash
source setup_rogue.sh
python -m pytest --cov
coverage report -m
codecov                            # Upload to codecov.io
```

**Coverage scope:** Only `pyrogue` Python package is measured. C++ code is not covered by Python coverage tools.

## C++ API Test

**Location:** `tests/api_test/`
**Build:** Separate CMake project
**Runner:** Standalone executable compiled against rogue C++ library

```bash
source setup_rogue.sh
cd tests/api_test
mkdir build; cd build
cmake ..
make
../../bin/api_test
```

This test exercises the `rogue::interfaces::api::Bsp` C++ API for tree navigation, variable get/set, YAML config, and bulk read/write operations.

## CI Integration

**GitHub Actions:** `.github/workflows/rogue_ci.yml`

**Test pipeline (full_build_test job):**
1. Check for trailing whitespace and tabs in `*.cpp`, `*.h`, `*.py`
2. Run Python/C++ linters (`scripts/run_linters.sh`)
3. Build rogue with CMake
4. Run `python -m pytest --cov`
5. Build and run C++ API test
6. Generate coverage report with codecov

**Additional CI jobs:**
- `small_build_test`: C++-only build without Python (`-DNO_PYTHON=1`)
- `macos_arm64_build_test`: macOS arm64 conda build + pytest (no coverage)

## Common Patterns

**Async/Polling in Tests:**
Stream tests use polling loops to wait for asynchronous frame delivery:
```python
for i in range(300):   # Wait up to 30 seconds
    if prbsRx.getRxCount() == FrameCount:
        break
    time.sleep(.1)
```

**Error Testing:**
Tests verify exceptions via try/except pattern:
```python
try:
    self.add(pyrogue.LocalVariable(
        name='var_without_value'))
    raise AssertionError('Expected exception not raised')
except Exception as e:
    print(type(e))  # do something with "e" for flake8
    pass
```

Newer tests use pytest-style assertion:
```python
try:
    root.myDevice.var.set('wrong-type')
    raise AssertionError('Changing a LocalVariable type did not raise an exception')
except pyrogue.VariableError as exc:
    assert 'typeCheck=False' in str(exc)
    assert 'expected' in str(exc)
```

**pytest monkeypatch (newer tests):**
```python
def test_logging_feedback(monkeypatch):
    with pr.Root(name='root', pollEn=False, maxLog=10) as root:
        monkeypatch.setattr(root.SystemLog, 'set', wrap('SystemLog', root.SystemLog.set))
        # ... test ...
```

**Performance Testing:**
```python
def _measure_operation(root, count, operation):
    start_ns = time.perf_counter_ns()
    _run_update_loop(root, count, operation)
    elapsed_ns = time.perf_counter_ns() - start_ns
    return {'avg_ns': float(elapsed_ns) / count}

# Assert against threshold
assert not failures, "Rate check failed:\n" + "\n".join(failures)
```

## Writing New Tests

**To add a new test:**
1. Create `tests/test_<feature>.py`
2. Add the license header
3. Define Device subclass(es) with register definitions
4. Define a Root subclass using `rogue.interfaces.memory.Emulate(4, 0x1000)` for memory emulation
5. Define `test_<name>()` functions using `with RootClass() as root:` context manager
6. Add `if __name__ == "__main__": test_<name>()` for standalone execution
7. Use `raise AssertionError(...)` or `assert` for verification
8. Set `pollEn=False` and `timeout=2.0` in root constructor

**No special registration needed** -- pytest auto-discovers `test_*.py` files in `tests/`.

---

*Testing analysis: 2026-03-24*
