# Coding Conventions

**Analysis Date:** 2026-03-24

## Languages

**Primary:** Python 3.6+ (`python/pyrogue/`) and C++14 (`src/rogue/`, `include/rogue/`)
**Build:** CMake 3.15+ (`CMakeLists.txt`)

## File Header

Every source file begins with a license header block. Follow these templates exactly.

**Python:**
```python
#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       [Module description]
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
```

**C++:**
```cpp
/**
 * ----------------------------------------------------------------------------
 * Company    : SLAC National Accelerator Laboratory
 * ----------------------------------------------------------------------------
 * Description:
 * [Module description]
 * ----------------------------------------------------------------------------
 * This file is part of the rogue software platform. It is subject to
 * the license terms in the LICENSE.txt file found in the top-level directory
 * of this distribution and at:
 *    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
 * No part of the rogue software platform, including this file, may be
 * copied, modified, propagated, or distributed except according to the terms
 * contained in the LICENSE.txt file.
 * ----------------------------------------------------------------------------
 **/
```

## Naming Patterns

### Python

**Files:**
- Core pyrogue module files use underscore prefix with PascalCase: `_Node.py`, `_Variable.py`, `_Device.py`, `_Root.py`
- Subpackage modules use underscore prefix with PascalCase or lowercase: `_Network.py`, `simulation.py`, `epicsV4.py`
- Test files use `test_` prefix with snake_case: `test_memory.py`, `test_localvars.py`

**Classes:**
- PascalCase: `Node`, `Device`, `Root`, `BaseVariable`, `BaseCommand`, `RemoteVariable`, `LocalVariable`
- Exception classes end with `Error`: `NodeError`, `VariableError`, `CommandError`, `GeneralError`
- Internal/helper classes also PascalCase: `VariableWaitClass`, `PollQueueEntry`, `UpdateTracker`

**Functions/Methods:**
- Public methods use camelCase: `addListener()`, `getDisp()`, `setDisp()`, `genFrame()`, `writeBlocks()`
- Private/internal methods use underscore prefix with camelCase: `_doUpdate()`, `_rootAttached()`, `_doTransaction()`
- Module-level helper functions use camelCase: `logInit()`, `logException()`, `streamConnect()`, `waitCntrlC()`
- Module-level utility functions use camelCase: `wordCount()`, `byteCount()`, `reverseBits()`
- Some module-level functions use camelCase matching their class: `startTransaction()`, `checkTransaction()`, `writeBlocks()`

**Variables:**
- Instance variables use underscore prefix for private: `self._value`, `self._lock`, `self._count`
- Public instance variables (rare) use camelCase without prefix: `self.path`, `self.name`
- Module-level constants use PascalCase or UPPER_CASE: `FrameCount`, `FrameSize`, `MaxCycles`, `BENCH_COUNT`

**Constructor Parameters:**
- Use camelCase for keyword arguments: `bitSize`, `bitOffset`, `memBase`, `pollEn`, `initRead`, `maxFileSize`

### C++

**Files:**
- PascalCase matching the class name: `Master.cpp`, `Slave.cpp`, `GeneralError.cpp`, `StreamWriter.cpp`
- Headers use `.h`, sources use `.cpp`
- Each module directory has a `module.cpp` for Python binding registration

**Classes:**
- PascalCase within nested namespaces: `rogue::interfaces::stream::Master`, `rogue::GeneralError`
- Wrapper classes for Python bindings append `Wrap`: `SlaveWrap`

**Functions/Methods:**
- camelCase: `addSlave()`, `reqFrame()`, `sendFrame()`, `acceptFrame()`, `slaveCount()`
- Static factory methods named `create()`: `Master::create()`, `Slave::create()`, `Logging::create()`
- Python binding setup methods named `setup_python()` (snake_case exception)
- Private members use trailing underscore: `slaves_`, `slaveMtx_`, `defSlave_`, `text_`, `level_`

**Namespaces:**
- Nested hierarchy matching directory structure: `rogue::interfaces::stream`, `rogue::utilities::fileio`
- Namespace aliases at file scope: `namespace ris = rogue::interfaces::stream;`, `namespace bp = boost::python;`

**Type Aliases:**
- `typedef std::shared_ptr<ClassName> ClassNamePtr;` at end of namespace block
- Example: `typedef std::shared_ptr<rogue::interfaces::stream::Master> MasterPtr;`

## Code Style

### Formatting

**Python:**
- Linter: flake8 (config: `.flake8`)
- Many whitespace rules are intentionally ignored (E201, E202, E221, E241, E251, E501, etc.) to allow alignment-based formatting
- No trailing whitespace (enforced in CI)
- No tab characters (enforced in CI) -- use spaces only
- Indentation: 4 spaces

**C++:**
- Linter: cpplint (config: `CPPLINT.cfg`), max line length 250
- Formatter: clang-format (config: `.clang-format`) based on Google style
- Column limit: 120
- Indent width: 4 spaces
- Pointer alignment: left (`int* ptr`)
- No tab characters (enforced in CI)
- No trailing whitespace (enforced in CI)

### Linting

**Python (`.flake8`):**
- Excludes: `__init__.py`, `rogue_plugin.py`
- Heavily relaxed whitespace rules to allow column-aligned parameter formatting
- Line length (E501) is not enforced

**C++ (`CPPLINT.cfg`):**
- Disabled checks: `legal/copyright`, `build/c++11`, `build/include_order`, `build/header_guard`, `whitespace/indent`, `runtime/arrays`, `runtime/references`
- Max line length: 250

**CI enforcement (`scripts/run_linters.sh`):**
- Compiles all Python files with `python -m compileall`
- Runs `flake8 --count` on `python/` and `tests/`
- Runs `cpplint` on all `.h` and `.cpp` files (excluding `build/`)
- CI also checks for trailing whitespace and tab characters separately

## Import Organization

### Python

**Order:**
1. `from __future__ import annotations` (when used)
2. Standard library imports (`sys`, `os`, `threading`, `time`, `logging`, `json`, `re`, etc.)
3. Third-party imports (`numpy as np`)
4. Package self-imports (`import pyrogue as pr`, `import rogue.interfaces.memory as rim`)
5. Relative imports from `collections` (`from collections import OrderedDict as odict`)

**Canonical aliases:**
- `import pyrogue as pr`
- `import rogue.interfaces.memory as rim`
- `import rogue.interfaces.stream as ris`
- `from collections import OrderedDict as odict`
- `import numpy as np`

**Star imports in `__init__.py`:**
- `python/pyrogue/__init__.py` uses `from pyrogue._Module import *` pattern for all core modules

### C++

**Order (enforced by `.clang-format` `IncludeCategories`):**
1. `"rogue/Directives.h"` (always first)
2. Own header (e.g., `"rogue/interfaces/stream/Master.h"`)
3. C headers (`<stdarg.h>`, `<stdint.h>`)
4. C++ headers (`<memory>`, `<string>`, `<vector>`)
5. Rogue headers (`"rogue/GeneralError.h"`, etc.)
6. Boost/Python headers (conditionally included under `#ifndef NO_PYTHON`)

**Path Aliases:**
- No TypeScript-style path aliases; imports use quoted relative paths: `#include "rogue/interfaces/stream/Master.h"`

## Error Handling

### Python

**Custom Exception Classes:**
- Defined per module: `NodeError` in `_Node.py`, `VariableError` in `_Variable.py`, `CommandError` in `_Command.py`
- All inherit from `Exception`
- Pattern:
```python
class ModuleError(Exception):
    """Raised when [specific condition] fails."""
    pass
```

**Error Logging:**
- Use `logException(log, e)` helper from `_Node.py` which distinguishes `MemoryError` from generic exceptions
- Pattern: `MemoryError` logged with `log.error()`, others with `log.exception()`

**Test Assertions:**
- Older tests use `raise AssertionError(...)` pattern (note: this is a historical spelling used consistently throughout)
- Newer tests use `assert` statements with messages
- Some tests use `try/except` blocks to verify expected exceptions

### C++

**Exception Class:**
- Single exception type: `rogue::GeneralError` inherits from `std::exception`
- Factory method: `GeneralError::create(src, fmt, ...)` with printf-style formatting
- Translated to Python exceptions via `setup_python()` and `translate()`
- Fixed buffer size of 600 chars for error messages

**GIL Management:**
- `rogue::GilRelease noGil;` used at the top of C++ methods that may block, to release the Python GIL
- `rogue::ScopedGil` for acquiring GIL when calling back into Python
- Pattern:
```cpp
void SomeClass::blockingMethod() {
    rogue::GilRelease noGil;
    std::lock_guard<std::mutex> lock(mtx_);
    // ... blocking work ...
}
```

## Logging

### Python

**Framework:** Python `logging` module, initialized via `logInit()` helper in `_Node.py`

**Logger Naming Convention:**
- All loggers prefixed with `pyrogue`
- Hierarchy: `pyrogue.{BaseClass}.{ClassName}.{path}` (e.g., `pyrogue.Variable.LocalVariable.root.myVar`)
- Base class tags: `Command`, `Variable`, `Root`, `Device`

**Initialization Pattern:**
```python
self._log = pr.logInit(cls=self, name=self.name, path=self.path)
```

### C++

**Framework:** Custom `rogue::Logging` class in `include/rogue/Logging.h`

**Levels:** `Critical=50`, `Error=40`, `Thread=35`, `Warning=30`, `Info=20`, `Debug=10`

**Pattern:**
```cpp
std::shared_ptr<rogue::Logging> log_ = rogue::Logging::create("rogue.interfaces.stream.Master");
log_->debug("Message: %s", data.c_str());
```

## Comments

**Python Docstrings:**
- Use NumPy-style docstrings with `Parameters`, `Returns`, `Raises` sections
- Class docstrings describe purpose and constructor parameters
- Method docstrings describe behavior and parameters
- Pattern:
```python
def method(self, param: int) -> bool:
    """Brief description.

    Parameters
    ----------
    param : int
        Description of param.

    Returns
    -------
    bool
        Description of return value.
    """
```

**C++ Doxygen:**
- Use `@brief`, `@details`, `@param`, `@return` tags
- Pattern:
```cpp
/**
 * @brief Brief description.
 *
 * @details
 * Extended description of behavior.
 *
 * @param name Description.
 * @return Description.
 */
```

**Inline comments:**
- C++ uses `//!` or `//` for inline/preceding comments
- Python uses `#` with optional alignment for column formatting

## Function Design

**Python Constructors:**
- Use keyword-only arguments (bare `*` in signature): `def __init__(self, *, name=None, description="", ...)`
- Forward unknown kwargs with `**kwargs`
- Call parent `__init__` explicitly: `pr.Device.__init__(self, **kwargs)` or `super().__init__(**kwargs)`

**C++ Factory Pattern:**
- Every class intended for shared ownership provides a `static create()` factory method
- Returns `std::shared_ptr<ClassName>`
- Constructors are public but documented as "low-level C++ allocation path"

**Python Decorator:**
- `@pr.expose` marks properties and methods for external interface (EPICS, ZMQ) visibility

## Module Design

**Python Exports:**
- Core modules use star exports from `__init__.py`
- Each module file (`_Node.py`, `_Variable.py`, etc.) defines public classes
- No `__all__` lists observed; all top-level names are exported

**C++ Module Registration:**
- Each directory has a `module.cpp` that calls `setup_python()` on all classes in that namespace
- Conditional compilation with `#ifndef NO_PYTHON` guards

**Variable Definition Pattern (critical for hardware register definitions):**
- Use column-aligned keyword arguments for readability:
```python
self.add(pr.RemoteVariable(
    name         = "RegisterName",
    offset       =  0x1c,
    bitSize      =  16,
    bitOffset    =  0x00,
    base         = pr.UInt,
    mode         = "RW",
))
```

## Thread Safety

**Python:**
- Use `threading.Lock()` for instance-level locking: `self._lock = threading.Lock()`
- Use `threading.Condition()` for wait/notify patterns: `self._cv = threading.Condition()`
- Use `with` statement for lock acquisition

**C++:**
- Use `std::mutex` with `std::lock_guard<std::mutex>` for RAII locking
- GIL release/acquire via `rogue::GilRelease` and `rogue::ScopedGil`

## Operator Overloading

**Stream connection operators:**
- Python `>>` and `<<` operators connect stream masters to slaves
- C++ equivalents: `operator>>` and `operator<<`
- Usage: `prbsTx >> fifo >> prbsRx` or `sim << ms`
- Defined in `Master` and `Slave` classes respectively

---

*Convention analysis: 2026-03-24*
