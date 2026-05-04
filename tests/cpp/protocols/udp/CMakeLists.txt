# Regression tests for UDP protocol candidates (plan 02-03).

rogue_add_cpp_test(rogue-cpp-protocols-udp-fd-setsize-audit-repro
   SOURCES
      test_udp_fd_setsize_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-protocols-udp-fd-setsize-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-protocols-udp-raw-thread-audit-repro
   SOURCES
      test_udp_raw_thread_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-protocols-udp-raw-thread-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
