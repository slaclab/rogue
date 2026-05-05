rogue_add_cpp_test(rogue-cpp-xvc-smoke
   SOURCES
      test_xvc_smoke.cpp
   LABELS
      xilinx
      requires-python
)
set_tests_properties(rogue-cpp-xvc-smoke PROPERTIES TIMEOUT 10)

rogue_add_cpp_test(rogue-cpp-protocols-jtag-driver-swallow-audit-repro
   SOURCES
      test_jtag_driver_swallow_audit_repro.cpp
   LABELS
      cpp-core
      requires-python
)
target_compile_definitions(rogue-cpp-protocols-jtag-driver-swallow-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
