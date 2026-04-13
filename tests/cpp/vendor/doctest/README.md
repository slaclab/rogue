# Vendored doctest

This directory vendors the upstream single-header `doctest` C++ test framework
for Rogue's native C++ test suite.

Upstream project:
- `https://github.com/doctest/doctest`

Imported version:
- `v2.4.12`

License:
- MIT

Notes:
- `doctest.h` is copied from the upstream tagged release and should not be
  edited for Rogue-local behavior.
- Rogue-specific test helpers and runner setup belong under `tests/cpp/support/`
  instead of in the vendored header.
