rogue_add_cpp_test(rogue-cpp-rssi-reqframe-error
   SOURCES
      test_reqframe_error.cpp
   LABELS
      cpp-core
      no-python
)
set_tests_properties(rogue-cpp-rssi-reqframe-error PROPERTIES TIMEOUT 10)
