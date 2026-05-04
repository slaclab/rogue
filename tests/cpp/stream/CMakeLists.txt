rogue_add_cpp_test(rogue-cpp-stream-frame-pool
   SOURCES
      test_frame_pool.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-stream-iterator
   SOURCES
      test_iterator.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-stream-flow-primitives
   SOURCES
      test_fifo_filter_rate_drop.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-stream-pool-raw-alloc-audit-repro
   SOURCES
      test_pool_raw_alloc_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-stream-pool-raw-alloc-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-stream-tcpcore-close-deprecated-audit-repro
   SOURCES
      test_tcpcore_close_deprecated_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-stream-tcpcore-close-deprecated-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-stream-streamzip-truncation-audit-repro
   SOURCES
      test_streamzip_truncation_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-stream-streamzip-truncation-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-stream-streamreader-close-deadlock-audit-repro
   SOURCES
      test_streamreader_close_deadlock_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-stream-streamreader-close-deadlock-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-stream-prbs-alloc-audit-repro
   SOURCES
      test_prbs_alloc_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-stream-prbs-alloc-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
