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

rogue_add_cpp_test(rogue-cpp-stream-tcpcore-close-deprecated-audit-repro
   SOURCES
      test_tcpcore_close_deprecated_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-stream-tcpcore-close-deprecated-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-stream-tcpcore-acceptframe-null-push-audit-repro
   SOURCES
      test_tcpcore_acceptframe_null_push_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-stream-tcpcore-acceptframe-null-push-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-stream-tcpcore-stop-serialization-audit-repro
   SOURCES
      test_tcpcore_stop_serialization_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-stream-tcpcore-stop-serialization-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
