# Legacy API Test Path

The old standalone `tests/api_test` build is no longer used.

The C++ API smoke test now lives in `tests/cpp/smoke/test_api_smoke.cpp` and
is built and executed through the main CMake/CTest flow:

- configure with `-DROGUE_BUILD_TESTS=ON`
- run `ctest --test-dir build --output-on-failure -L requires-python`
