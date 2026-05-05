rogue_add_cpp_test(rogue-cpp-version
   SOURCES
      test_version.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-atomic-thread-flags
   SOURCES
      test_atomic_thread_flags.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-ctor-catch-thread-cleanup
   SOURCES
      test_ctor_catch_thread_cleanup.cpp
   LABELS
      cpp-core
      no-python
)

rogue_add_cpp_test(rogue-cpp-logging-filter-leak-audit-repro
   SOURCES
      test_logging_filter_leak_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-logging-filter-leak-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-logging-lock-guard-audit-repro
   SOURCES
      test_logging_lock_guard_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-logging-lock-guard-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-version-init-race-audit-repro
   SOURCES
      test_version_init_race_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-version-init-race-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-queue-empty-thread-safety-audit-repro
   SOURCES
      test_queue_empty_thread_safety_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-queue-empty-thread-safety-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")

rogue_add_cpp_test(rogue-cpp-helpers-deprecated-audit-repro
   SOURCES
      test_helpers_deprecated_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-helpers-deprecated-audit-repro
   PRIVATE ROGUE_SRC_DIR="${CMAKE_SOURCE_DIR}")
