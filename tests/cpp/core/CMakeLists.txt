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

# Needs the Python runtime and finalizes it, so it cannot share a binary.
if (NOT NO_PYTHON)
   rogue_add_cpp_test(rogue-cpp-logging-python-after-finalize
      SOURCES
         test_logging_python_after_finalize.cpp
      LABELS
         cpp-core
         requires-python
   )

   set_tests_properties(rogue-cpp-logging-python-after-finalize PROPERTIES TIMEOUT 30)
endif()
