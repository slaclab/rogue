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

rogue_add_cpp_test(rogue-cpp-queue-thread-safety-audit-repro
   SOURCES
      test_queue_empty_thread_safety_audit_repro.cpp
   LABELS
      cpp-core
      no-python
)
target_compile_definitions(rogue-cpp-queue-thread-safety-audit-repro
   PRIVATE ROGUE_SRC_DIR="${PROJECT_SOURCE_DIR}")
# Bound any hang from a regression that leaves a producer parked in pushCond_.wait().
set_tests_properties(rogue-cpp-queue-thread-safety-audit-repro
   PROPERTIES TIMEOUT 60)
