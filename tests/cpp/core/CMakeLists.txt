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
# Bound the cleanup path: the audit's behavioural cases use unconditional
# join() after stop(), so a regression that leaves a producer parked in
# pushCond_.wait() would otherwise hang ctest indefinitely (no global
# --timeout in CI).  60 s is well above the suite's normal wall-clock cost
# (~tens of seconds, dominated by bounded waits) and bounds any hang.
set_tests_properties(rogue-cpp-queue-thread-safety-audit-repro
   PROPERTIES TIMEOUT 60)
