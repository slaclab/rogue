# Isolated in its own binary because an unpatched library aborts the process.
rogue_add_cpp_test(rogue-cpp-udp-rx-before-ownership
   SOURCES
      test_udp_rx_before_ownership.cpp
   LABELS
      cpp-core
      no-python
)
set_tests_properties(rogue-cpp-udp-rx-before-ownership PROPERTIES TIMEOUT 10)

rogue_add_cpp_test(rogue-cpp-udp-server-peer-before-delivery
   SOURCES
      test_udp_server_peer_before_delivery.cpp
   LABELS
      cpp-core
      no-python
)
set_tests_properties(rogue-cpp-udp-server-peer-before-delivery PROPERTIES TIMEOUT 10)
