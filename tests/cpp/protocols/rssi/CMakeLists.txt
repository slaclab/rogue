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

rogue_add_cpp_test(rogue-cpp-rssi-ack-window
   SOURCES
      test_ack_window.cpp
   LABELS
      cpp-core
      no-python
)
set_tests_properties(rogue-cpp-rssi-ack-window PROPERTIES TIMEOUT 30)

# Linux only: loopback UDP timing on the GitHub macOS runners is too jittery.
if (CMAKE_SYSTEM_NAME STREQUAL "Linux")
   rogue_add_cpp_test(rogue-cpp-rssi-send-order
      SOURCES
         test_send_order.cpp
      LABELS
         integration
         no-python
   )
   set_tests_properties(rogue-cpp-rssi-send-order PROPERTIES TIMEOUT 60)
endif()
