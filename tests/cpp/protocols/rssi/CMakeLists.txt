# Regression tests for RSSI protocol candidates (plan 02-03).

rogue_add_cpp_test(rogue-cpp-protocols-rssi-thread-audit-repro
   SOURCES
      test_rssi_thread_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-protocols-rssi-thread-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-protocols-rssi-busyloop-audit-repro
   SOURCES
      test_rssi_busyloop_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-protocols-rssi-busyloop-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
