rogue_add_cpp_test(rogue-cpp-rssi-reqframe-error
   SOURCES
      test_reqframe_error.cpp
   LABELS
      cpp-core
      no-python
)
set_tests_properties(rogue-cpp-rssi-reqframe-error PROPERTIES TIMEOUT 10)

rogue_add_cpp_test(rogue-cpp-rssi-client-server-release
   SOURCES
      test_client_server_release.cpp
   LABELS
      cpp-core
      no-python
)
set_tests_properties(rogue-cpp-rssi-client-server-release PROPERTIES TIMEOUT 10)
